#!/usr/bin/env python

import argparse
import atexit
import hashlib
import ipaddress
import json
import os
import pprint
from pyVim import connect
from pyVmomi import vim
import requests
import shutil
import socket
import subprocess
import sys
import time
import urllib3
import yaml
from pyVim.task import WaitForTask


def parse_args():
    """ Parse command line arguments """
    parser = argparse.ArgumentParser(description="Process args")

    # Mandatory options
    parser.add_argument("action", nargs="?", choices=["plan", "deploy", "destroy", "listimages", "pushimage"],
                        help="Execution command")
    parser.add_argument("--var-file", nargs="?", required=False, action="store",
                        help="Deployment customization file")
    parser.add_argument("--stack-name", nargs="?", required=False, action="store",
                        help="Name of the stack")
    parser.add_argument("--guest-id", nargs="?", required=False, action="store",
                        help="Guest operating system identifier")
    parser.add_argument("--state-file-dir", nargs="?", required=False, action="store",
                        help="Directory used to save state file")

    parser.add_argument("--media-type", nargs="?", choices=["iso", "vmdk"], required=False,
                        help="Choose installation media type")
    parser.add_argument("--media", nargs="?", required=False, action="store",
                        help="Installation media name")
    parser.add_argument("--media-dir", nargs="?", required=False, action="store",
                        help="Media directory on the datastore")
    parser.add_argument("--source-media", nargs="?", required=False, action="store",
                        help="Source media to upload to the remote media directory")

    # cloud-init
    parser.add_argument("--admin-cloud-init", nargs="?", required=False, action="store",
                        help="Path to the cloud-init config file for the admin node")
    parser.add_argument("--node-cloud-init", nargs="?", required=False, action="store",
                        help="Path to the cloud-init config file for the master and worker nodes")

    # vCenter
    parser.add_argument("--vc-host", nargs="?", required=False, action="store",
                        help="vCenter host to connect to")
    parser.add_argument("--vc-port", nargs="?", required=False, action="store",
                        help="vCenter host port")
    parser.add_argument("--vc-username", nargs="?", required=False, action="store",
                        help="vCenter username")
    parser.add_argument("--vc-password", nargs="?", required=False, action="store",
                        help="vCenter password")
    parser.add_argument("--vc-insecure", nargs="?", required=False, action="store",
                        choices=[True, False],
                        help="Disable certificate verification")
    parser.add_argument("--vc-datacenter", nargs="?", required=False, action="store",
                        help="Datacenter to use")
    parser.add_argument("--vc-datastore", nargs="?", required=False, action="store",
                        help="Datastore to use")
    parser.add_argument("--vc-network", nargs="?", required=False, action="store",
                        help="Network for the virtual machines")
    parser.add_argument("--vc-resource-pool", nargs="?", required=False, action="store",
                        help="Resource pool for the virtual machines")

    # Admin
    parser.add_argument("--admin-prefix", nargs="?", required=False, action="store",
                        help="Admin node name prefix")
    parser.add_argument("--admin-cpu", nargs="?", required=False, action="store",
                        help="Admin CPUs")
    parser.add_argument("--admin-ram", nargs="?", required=False, action="store",
                        help="Admin RAM")

    # Masters
    parser.add_argument("--master-count", nargs="?", required=False, action="store",
                        help="Number of masters")
    parser.add_argument("--master-prefix", nargs="?", required=False, action="store",
                        help="Master node name prefix")
    parser.add_argument("--master-cpu", nargs="?", required=False, action="store",
                        help="Master CPUs")
    parser.add_argument("--master-ram", nargs="?", required=False, action="store",
                        help="Master RAM")

    # Workers
    parser.add_argument("--worker-count", nargs="?", required=False, action="store",
                        help="Number of workers")
    parser.add_argument("--worker-prefix", nargs="?", required=False, action="store",
                        help="Worker node name prefix")
    parser.add_argument("--worker-cpu", nargs="?", required=False, action="store",
                        help="Worker CPUs")
    parser.add_argument("--worker-ram", nargs="?", required=False, action="store",
                        help="Worker RAM")

    args = parser.parse_args()
    return(args)


def load_yaml(yaml_file):
    """ Load file and read yaml """
    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            content = yaml.load(f)
        return(content)
    except IOError as e:
        Log.error("I/O error: {0}".format(e))
    except yaml.YAMLError as ey:
        Log.error("Error in yaml file: {0}".format(ey))


def get_user_opt(args):
    """ Merge options from file and from cli """
    if not args.var_file:
        args.var_file = "caasp-vmware.yaml"

    user_opt = load_yaml(args.var_file)
    # override values if argument from command line
    for k, v in vars(args).items():
        if v:
            user_opt[k] = v

    # Set default values if not provided on cli or in config file
    if "state_file_dir" not in user_opt:
        user_opt["state_file_dir"] = None

    # Allow getting credentials from environment user_opt
    if os.environ.get("VC_HOST") is not None:
        user_opt["vc_host"] = os.environ.get("VC_HOST")

    if os.environ.get("VC_USERNAME") is not None:
        user_opt["vc_username"] = os.environ.get("VC_USERNAME")

    if os.environ.get("VC_PASSWORD") is not None:
        user_opt["vc_password"] = os.environ.get("VC_PASSWORD")

    # Generate values
    user_opt["admin_count"] = 1
    user_opt["admin_node"] = "{0}-{1}".format(
        user_opt["admin_prefix"], user_opt["stack_name"])
    user_opt["master_node"] = "{0}-{1}".format(
        user_opt["master_prefix"], user_opt["stack_name"])
    user_opt["worker_node"] = "{0}-{1}".format(
        user_opt["worker_prefix"], user_opt["stack_name"])
    return user_opt


def generate_config(user_opt):
    """ Generate the configuration for the deployement """
    config = {}
    config["parameters"] = user_opt
    config["admin"] = {"vmguests": [], "config": {}}
    config["master"] = {"vmguests": [], "config": {}}
    config["worker"] = {"vmguests": [], "config": {}}

    stack_name = config["parameters"]["stack_name"]
    config["parameters"]["vm_deploy_dir"] = "caasp-{0}".format(stack_name)

    # Used for the local deployment dir in /tmp 
    stack_hash = hashlib.md5(stack_name.encode('utf-8')).hexdigest()

    # The API needs a / to know it is a directory
    media_dir = config["parameters"]["media_dir"]
    if media_dir[-1] is not "/":
        config["parameters"]["media_dir"] = "{0}/".format(media_dir)

    def append(conf_dict, node_count, node_name, role, ram, cpu, cloud_init_file):
        """
        'master': {
          'config': {
            'cloud_init_file': 'cloud-init.cls',
            'ds_cloud_iso_path': 'caasp-pyvomi/caasp-master-pyvomi.iso',
            'instance_id': 'master',
            'iso_filename': 'caasp-master-pyvomi.iso',
            'path': '/tmp/3772b45d891d0f9d14ddef20c3fd03db/master',
            'stack_hash': '3772b45d891d0f9d14ddef20c3fd03db',
            'stack_name': 'pyvomi'},
          'vmguests': [ { 
            'cpu': 2,
            'name': 'caasp-master-pyvomi000',
            'ram': 4096,
            'role': 'master'}]}
        """

        conf_dict[role]["config"]["stack_name"] = stack_name
        conf_dict[role]["config"]["stack_hash"] = stack_hash

        conf_dict[role]["config"]["path"] = "/tmp/{0}/{1}".format(
            stack_hash, role)

        conf_dict[role]["config"]["cloud_init_file"] = cloud_init_file

        iso_filename = "{0}.iso".format(node_name)
        conf_dict[role]["config"]["iso_filename"] = iso_filename
        conf_dict[role]["config"]["instance_id"] = role

        conf_dict[role]["config"]["ds_cloud_iso_path"] = "caasp-{0}/{1}".format(
            stack_name, iso_filename)

        for n in range(0, node_count):
            name = node_name + "%03d" % n
            conf_dict[role]["vmguests"].append({
                'name': name,
                'role': role,
                'ram': ram,
                'cpu': cpu,
            })

    append(config, user_opt["admin_count"], user_opt["admin_node"],
           "admin", user_opt["admin_ram"], user_opt["admin_cpu"], user_opt["admin_cloud_init"])
    append(config, user_opt["master_count"], user_opt["master_node"],
           "master", user_opt["master_ram"], user_opt["master_cpu"], user_opt["node_cloud_init"])
    append(config, user_opt["worker_count"], user_opt["worker_node"],
           "worker", user_opt["worker_ram"], user_opt["worker_cpu"], user_opt["node_cloud_init"])

    return config


class Log(object):
    @staticmethod
    def subtask(message):
        print("INFO: {0}".format(message))

    @staticmethod
    def task(message):
        print("TASK: {0}".format(message))

    @staticmethod
    def info(message):
        print("INFO: {0}".format(message))

    @staticmethod
    def warning(message):
        print("WARNING: {0}".format(message))

    @staticmethod
    def error(message):
        sys.exit("ERROR: {0}".format(message))


def get_obj(service_instance, viewType, obj_name, content=None):
    """ Return an object from ServiceInstance """
    recursive = True
    obj = None
    if not content:
        content = service_instance.RetrieveContent()
    container = content.rootFolder
    containerView = content.viewManager.CreateContainerView(
        container, viewType, recursive)
    for o in containerView.view:
        if o.name == obj_name:
            obj = o
            break
    containerView.Destroy()
    return obj


class VSphere(object):
    def __init__(self, vsphere):
        self.host = vsphere["vc_host"]
        self.port = vsphere["vc_port"]
        self.username = vsphere["vc_username"]
        self.password = vsphere["vc_password"]
        self.insecure = vsphere["vc_insecure"]
        self.datacenter_name = vsphere["vc_datacenter"]
        self.datastore_name = vsphere["vc_datastore"]
        self.network_name = vsphere["vc_network"]
        self.resource_pool_name = vsphere["vc_resource_pool"]

        self.service_intance = self.connect()
        self.content = self._content()
        self.datacenter = self.get_datacenter()
        self.datastore = self.get_datastore()
        self.network = self.get_network()
        self.resource_pool = self.get_resource_pool()
        self.storage_manager = self.get_storage_manager()
        self.file_manager = self.get_file_manager()

    # Connect to vCenter
    def connect(self):
        Log.task("log in to vcenter".format(self.host))
        Log.info("connecting...")
        try:
            if self.insecure is False:
                service_instance = connect.SmartConnect(
                    host=self.host,
                    user=self.username,
                    pwd=self.password,
                    port=int(self.port)
                )
                atexit.register(connect.Disconnect, service_instance)
                self.service_instance = service_instance
                Log.info("connection succeeded".format(self.host))
                return service_instance
            elif self.insecure is True:
                service_instance = connect.SmartConnectNoSSL(
                    host=self.host,
                    user=self.username,
                    pwd=self.password,
                    port=int(self.port)
                )
                atexit.register(connect.Disconnect, service_instance)
                self.service_instance = service_instance
                Log.info("connection succeeded".format(self.host))
                return service_instance
        except Exception as e:
            Log.error("connection failed: {0}".format(e))

    def _content(self):
        return self.service_instance.RetrieveContent()

    def get_datacenter(self):
        """ vim.Datacenter """
        datacenter = None
        datacenter = get_obj(self.service_instance, [
                             vim.Datacenter], self.datacenter_name, self.content)

        if not datacenter:
            Log.error("datacenter not found: {0}".format(
                self.datacenter_name))

        return datacenter

    def get_datastore(self):
        """ vim.Datastore """
        datastore = None
        for ds in self.datacenter.datastoreFolder.childEntity:
            if ds.name == self.datastore_name:
                datastore = ds
                break

        if not datastore:
            Log.error("datastore not found: {0}".format(
                self.datastore_name))

        return datastore

    def get_network(self):
        """ vim.Network """
        network = None
        network = get_obj(self.service_instance, [
                          vim.Network], self.network_name, self.content)

        if not network:
            Log.error("network not found: {0}".format(self.network_name))
        return network

    def get_resource_pool(self):
        """ vim.ResourcePool """
        resource_pool = None
        resource_pool = get_obj(self.service_instance, [
                                vim.ResourcePool], self.resource_pool_name, self.content)

        if not resource_pool:
            Log.error("resource pool not found: {0}".format(
                self.resource_pool_name))

        return resource_pool

    def get_storage_manager(self):
        """ vim.VirtualDiskManager """
        content = self.service_instance.RetrieveServiceContent()
        self.storage_manager = content.virtualDiskManager
        return content.virtualDiskManager

    def get_file_manager(self):
        """ vim.FileManager """
        content = self.service_instance.RetrieveServiceContent()
        self.file_manager = content.fileManager
        return content.fileManager


class CloudInit(object):
    """ Create and Push cloud init iso to datastore """

    @staticmethod
    def create_iso(role_config, admin_ip=None):
        path = role_config["path"]
        iso_filename = role_config["iso_filename"]
        iso_path = "{0}/{1}".format(role_config["path"],
                                    role_config["iso_filename"])
        instance_id = role_config["instance_id"]
        cloud_init_file = role_config["cloud_init_file"]

        Log.task("create cloud-init iso: {0}".format(instance_id))
        if not os.path.exists(iso_path):
            if not os.path.exists(path):
                os.makedirs(path)

            try:
                Log.info("generating metada-data")
                with open("{0}/meta-data".format(path), "w", encoding="utf-8") as f:
                    f.write(
                        "instance-id: {0}\nlocal-hostname: caasp".format(instance_id))

                Log.info("generating user-data")
                with open(cloud_init_file, "r", encoding="utf-8") as f:
                    if admin_ip:
                        user_data = f.read().replace("SET_ADMIN_NODE", admin_ip)
                    else:
                        user_data = f.read()

                with open("{0}/user-data".format(path), "w", encoding="utf-8") as f:
                    f.write(user_data)

                Log.info("creating iso")
                subprocess.run("genisoimage -output {0} -volid cidata -joliet -rock user-data meta-data >/dev/null 2>&1".format(
                    iso_filename), cwd=path, shell=True, check=True)
                Log.info("iso successfully created")
            except IOError as e:
                Log.error("i/o error: {0}".format(e))
            except subprocess.SubprocessError as es:
                Log.error(
                    "shelling out to genisoimage failed: {0}".format(es))
        else:
            Log.info("iso already created")

    @staticmethod
    def push_iso(vsphere, role_config):
        iso_path = "{0}/{1}".format(role_config["path"],
                                    role_config["iso_filename"])

        Log.task("push cloud-init iso to the datastore")
        Datastore.upload_file(
            vsphere, iso_path, role_config["ds_cloud_iso_path"])


class HttpRequest(object):
    def __init__(self, **kwargs):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.http_url = kwargs["http_url"]
        self.params = kwargs.get("params", None)
        self.headers = kwargs.get("headers", None)
        self.cookies = kwargs.get("cookies", None)
        self.verify = kwargs.get("verify", True)

        self.http = requests.Session()

    def head(self):
        try:
            request = self.http.head(self.http_url, params=self.params,
                                     headers=self.headers, cookies=self.cookies,
                                     verify=self.verify)
            return request.status_code
        except (ConnectionError, requests.HTTPError, requests.Timeout) as e:
            Log.error("connection failed: {0}".format(e))

    def get(self, **kwargs):
        try:
            request = self.http.get(self.http_url, params=self.params,
                                    headers=self.headers, cookies=self.cookies,
                                    verify=self.verify, allow_redirects=True, **kwargs)
            request.raise_for_status()
            return request
        except (ConnectionError, requests.HTTPError, requests.Timeout) as e:
            Log.error("connection failed: {0}".format(e))

    def put(self, **kwargs):
        try:
            request = self.http.put(self.http_url, params=self.params,
                                    headers=self.headers, cookies=self.cookies,
                                    verify=self.verify, **kwargs)
            request.raise_for_status()
            return request
        except (ConnectionError, requests.HTTPError, requests.Timeout) as e:
            Log.error("connection failed: {0}".format(e))

    def close(self):
        self.http.close()


class Datastore(object):
    @staticmethod
    def upload_file(vsphere, src_file, remote_file):
        """ Upload a file to a datastore using HTTP direct access """
        params = {"dsName": vsphere.datastore.info.name,
                  "dcPath": vsphere.datacenter.name}
        resource = "folder/{0}".format(remote_file)
        http_url = "https://{0}:443/{1}".format(vsphere.host, resource)

        # Make a cookie from vmware_soap_session="697a89a"; Path=/; HttpOnly; Secure;
        client_cookie = vsphere.service_instance._stub.cookie
        cookie = dict()
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie["vmware_soap_session"] = cookie_value

        # Get the request headers set up
        headers = {'Content-Type': 'application/octet-stream'}

        # Toggle the boolean insecure
        verify_cert = not vsphere.insecure

        remote_file_req = HttpRequest(http_url=http_url, params=params,
                                      headers=headers, cookies=cookie,
                                      verify=verify_cert)

        remote_file_exists = remote_file_req.head()

        Log.info("- source: {0}".format(src_file))
        Log.info("- destination: [{0}]{1}".format(vsphere.datastore.info.name,
                                                  remote_file))
        if remote_file_exists == 404:
            Log.info("uploading...")
            if src_file[:4] == "http":
                file_url = HttpRequest(http_url=src_file)
                f = file_url.get(stream=True)
                remote_file_req.put(data=f)
            else:
                with open(src_file, "rb") as f:
                    remote_file_req.put(data=f)

            Log.info("file upload succeeded")
            remote_file_req.close()
        else:
            Log.info("file already exists on the datastore")

    @staticmethod
    def path_exists(vsphere, path):
        """ Check if a file or folder exists on a datastore """
        path_exist = False

        # datastore path = [datastore]path/media.vmdk
        datastore = "[{0}]".format(vsphere.datastore.name)
        datastore_path = datastore + path
        folder_path = os.path.split(datastore_path)[0]
        file_name = os.path.split(datastore_path)[1]

        # use datastore root folder
        if not folder_path:
            folder_path = datastore

        # only search for the folder path
        if file_name == "":
            file_name = None

        spec = vim.host.DatastoreBrowser.SearchSpec(matchPattern=file_name)
        task = vsphere.datastore.browser.SearchDatastore_Task(
            datastorePath=folder_path, searchSpec=spec)
        try:
            WaitForTask(task)
            result = task.info.result
            for f in result.file:
                if f.path == file_name:
                    path_exist = True
                    return path_exist
                    break
            # it means at least the directory exists
            if not file_name:
                path_exist = True
        except vim.fault.FileNotFound as e:
            path_exist = False
        except vim.fault.InvalidDatastore as e:
            Log.error(
                "operation cannot be performed on the target datastore: {0}".format(e))
        finally:
            return path_exist

    @staticmethod
    def list_path(vsphere, path, match_pattern=None):
        """ Check if a file or folder exists on a datastore """

        datastore = "[{0}]".format(vsphere.datastore.name)
        datastore_path = datastore + path
        files = []

        spec = vim.host.DatastoreBrowser.SearchSpec(matchPattern=match_pattern)
        task = vsphere.datastore.browser.SearchDatastore_Task(
            datastorePath=datastore_path, searchSpec=spec)

        try:
            WaitForTask(task)
            result = task.info.result
            for f in result.file:
                files.append(f.path)
        except vim.fault.FileNotFound:
            Log.error("path does not exist: {0}".format(datastore_path))

        return files

    @staticmethod
    def create_dir(vsphere, path):
        """ Create a directory in a datastore """

        # datastore path = [datastore]path/
        datastore = "[{0}]".format(vsphere.datastore.name)
        datastore_path = datastore + path

        Log.task("create directory: {0}".format(datastore_path))
        try:
            Log.info("creating...")
            vsphere.file_manager.MakeDirectory(
                datacenter=vsphere.datacenter,
                name=datastore_path)
            Log.info("creation succeeded")
        except vim.fault.FileAlreadyExists:
            Log.info("directory already exists, nothing to do")

    @staticmethod
    def delete_path(vsphere, path):
        """ Delete a file or a directory in a datastore """

        # datastore path = [datastore]path/
        datastore = "[{0}]".format(vsphere.datastore.name)
        datastore_path = datastore + path

        task = vsphere.file_manager.DeleteDatastoreFile_Task(
            datacenter=vsphere.datacenter,
            name=datastore_path)

        Log.task("delete path: {0}".format(datastore_path))
        try:
            Log.info("deleting...")
            WaitForTask(task)
            Log.info("deletion succeeded")
        except vim.fault.FileNotFound:
            Log.info("path not found, nothing to do")
        except vim.fault.CannotDeleteFile as e:
            Log.error("file deletion failed: {0}".format(e))
        except vim.fault.FileLocked:
            Log.error("file is locked or in use")


class VMachine(object):
    recursive = True
    vm_obj = None
    vmdk = None

    def __init__(self, vsphere, common_config, role_config, vm_config):
        self.vsphere = vsphere
        self.role_config = role_config
        self.vm_config = vm_config

        self.name = vm_config["name"]
        self.template_name = vm_config["name"][:-3]
        self.role = vm_config["role"]
        self.ram = vm_config["ram"]
        self.cpu = vm_config["cpu"]

        self.datastore_path = "[{0}]".format(common_config["vc_datastore"])
        self.datastore_name = common_config["vc_datastore"]

        self.cloud_init_path = "[{0}]{1}".format(common_config["vc_datastore"],
                                                 role_config["ds_cloud_iso_path"])

        self.vm_path = "[{0}] {1}/{2}/{2}.vmx".format(common_config["vc_datastore"],
                                                      common_config["vm_deploy_dir"],
                                                      vm_config["name"])

        self.vm_template_path = "[{0}] {1}/{2}/{2}.vmx".format(common_config["vc_datastore"],
                                                               common_config["vm_deploy_dir"],
                                                               vm_config["name"][:-3])

        self.media_type = common_config["media_type"]
        self.media_name = common_config["media"]
        self.media_path = "[{0}]{1}".format(
            common_config["vc_datastore"], common_config["media"])

        self.guest_id = common_config["guest_id"]

        self.service_instance = vsphere.service_instance
        self.datacenter = vsphere.datacenter
        self.datastore = vsphere.datastore
        self.network = vsphere.network
        self.resource_pool = vsphere.resource_pool
        self.storage_manager = vsphere.storage_manager
        self.file_manager = vsphere.file_manager

        self.vm_obj = self.get_vm()

    def get_vm(self, isTemplate=False):
        """ Return VirtualMachine object from a Datacenter """
        vm = None

        if isTemplate:
            vm_name = self.template_name
        else:
            vm_name = self.name

        for vm in self.datacenter.vmFolder.childEntity:
            if vm.name == vm_name:
                return vm

    def _check_media(self):
        """ Check if the media exists on a datastore """
        media_exists = Datastore.path_exists(self.vsphere, self.media_name)
        if media_exists:
            return media_exists
        else:
            Log.error("media file not found: {0}".format(
                self.media_name))

    def _copy_vmdk(self):
        """ Copy original vmdk media to the vm folder """
        if self._check_media():
            dest_path = "{0}/{1}.vmdk".format(self.vm_path, self.name)
            task = self.storage_manager.CopyVirtualDisk_Task(sourceName=self.media_path,
                                                             sourceDatacenter=self.datacenter,
                                                             destDatacenter=self.datacenter,
                                                             destName=dest_path)
            Log.subtask("copy vmdk")
            Log.info("- source:".format(self.media_path))
            Log.info("- destination:".format(self.dest_path))
            try:
                Log.info("copying...")
                WaitForTask(task, self.service_instance)
                Log.info("copy succeded")
            except Exception as e:
                Log.error("copy error: {0}".format(e))

    def get_ip(self):
        """ Get first IPv4 available on the first NIC """
        self.vm_obj = self.get_vm()
        ip = None

        if self.vm_obj.guest.net:
            for i in self.vm_obj.guest.net[0].ipAddress:
                if ipaddress.ip_address(i).version == 4:
                    ip = i
                    break
            return ip
        else:
            return ip

    def create_vm(self, isTemplate=False):
        """
        Create a VM, name is set to template_name
        if isTemplate is set to True 
        """
        # CheckVmConfig_Task(checkVmConfig)

        self.vm_obj = self.get_vm(isTemplate)
        if isTemplate:  # use origin media
            vm_name = self.template_name
            vm_path_name = self.vm_template_path
            vdisk_file_name = self.media_path
        else:
            vm_name = self.name
            vm_path_name = self.vm_path
            vdisk_file_name = "{0}/{1}.vmdk".format(self.vm_path, vm_name)

        Log.subtask("create virtual machine: {0}".format(vm_name))

        if self.vm_obj:
            Log.error("virtual machine not found")
        else:
            vmx_file = vim.vm.FileInfo(logDirectory=None,
                                       snapshotDirectory=None,
                                       suspendDirectory=None,
                                       vmPathName=vm_path_name)
            device_operation = vim.vm.device.VirtualDeviceSpec.Operation.add

            # Add IDE disk controller
            virtual_ide_controller = vim.vm.device.VirtualIDEController(
                busNumber=0, key=0, unitNumber=0)
            virtual_ide_controller_spec = vim.vm.device.VirtualDeviceSpec(
                device=virtual_ide_controller,
                operation=device_operation)

            # Add vmdk virtual disk
            virtual_ide_dev = vim.vm.device.VirtualDisk(
                backing=vim.vm.device.VirtualDevice.FileBackingInfo(
                    datastore=self.datastore,
                    fileName=vdisk_file_name),
                controllerKey=0, key=0, unitNumber=0)
            virtual_ide_spec = vim.vm.device.VirtualDeviceSpec(device=virtual_ide_dev,
                                                               operation=device_operation)

            # Add virtual CDROM
            if self.media_type == "iso":
                iso_file_name = self.media_path
            else:
                iso_file_name = self.cloud_init_path

            virtual_cdrom_dev = vim.vm.device.VirtualCdrom(
                backing=vim.vm.device.VirtualCdrom.IsoBackingInfo(
                    datastore=self.datastore,
                    fileName=iso_file_name),
                controllerKey=0, key=1, unitNumber=1)

            virtual_cdrom_spec = vim.vm.device.VirtualDeviceSpec(
                device=virtual_cdrom_dev,
                operation=device_operation)

            # Add VMXNET3 ethernet card
            virtual_eth_dev = vim.vm.device.VirtualVmxnet3(
                backing=vim.vm.device.VirtualEthernetCard.NetworkBackingInfo(
                    deviceName=self.network.name,
                    network=self.network),
                connectable=vim.vm.device.VirtualDevice.ConnectInfo(startConnected=True))

            virtual_eth_spec = vim.vm.device.VirtualDeviceSpec(device=virtual_eth_dev,
                                                               operation=device_operation)
            # Add disk.enableUUID=1
            enable_uuid = vim.option.OptionValue(key="disk.enableUUID", value=1)

            vm_spec = vim.vm.ConfigSpec(
                name=vm_name, guestId=self.guest_id,
                memoryMB=self.ram, numCPUs=self.cpu,
                extraConfig=[enable_uuid], files=vmx_file,
                deviceChange=[virtual_ide_controller_spec,
                              virtual_ide_spec, virtual_eth_spec, virtual_cdrom_spec],
                version="vmx-11")

            task = self.datacenter.vmFolder.CreateVM_Task(
                config=vm_spec, pool=self.resource_pool)
            try:
                Log.info("creating...".format(vm_name))
                WaitForTask(task, self.service_instance)
                Log.info("creation succeeded".format(vm_name))
                self.vm_obj = self.get_vm(isTemplate)
            except Exception as e:
                Log.error("creation error: {0}".format(e))

    def create_vm_template(self, isTemplate=True):
        """ Wrapper to create a VM and mark it as a Template """
        self.vm_obj = self.get_vm(isTemplate)

        if not self.vm_obj:
            self.create_vm(isTemplate)
            Log.info("marking as template...")
            self.vm_obj.MarkAsTemplate()
            Log.info("marking succeeded")

    def delete(self):
        """ Delete a VM """
        Log.subtask("delete virtual machine: {0}".format(self.name))
        if self.vm_obj:
            try:
                Log.info("deleting...")
                task = self.vm_obj.Destroy_Task()
                WaitForTask(task, self.service_instance)
                self.vm_obj = self.get_vm()
                Log.info("deletion succeded")
            except Exception as e:
                Log.error("deletion failed: ".format(e))
        else:
            Log.info("virtual machine not found")

    def unregister(self, isTemplate=False):
        """ Unregister a VM or a VM Template """
        self.vm_obj = self.get_vm(isTemplate)
        if isTemplate:
            vm_name = self.template_name
        else:
            vm_name = self.name

        Log.subtask("unregister virtual machine: {0}".format(vm_name))
        if self.vm_obj:
            try:
                Log.info("unregistering...")
                self.vm_obj.UnregisterVM()
                self.vm_obj = self.get_vm(isTemplate)
                Log.info("unregistration succeded")
            except Exception as e:
                Log.error("unregistration failed: {0}".format(e))
        else:
            Log.info("virtual machine not found")

    def power_on(self):
        """ Power-on a VM """
        Log.subtask("power-on virtual machine: {0}".format(self.name))

        if not self.vm_obj.runtime.powerState == "poweredOn":
            try:
                Log.info("powering-on...")
                task = self.vm_obj.PowerOnVM_Task()
                WaitForTask(task, self.service_instance)
                self.vm_obj = self.get_vm()
                Log.info("powering-on succeded")
            except Exception as e:
                Log.error("powering-on failed: {0}".format(e))
        else:
            Log.info("virtual machine already powered-on")

    def power_off(self):
        """ Power-off a VM """
        Log.subtask("power-off virtual machine: {0}".format(self.name))

        self.vm_obj = self.get_vm()
        if self.vm_obj:
            if self.vm_obj.runtime.powerState == "poweredOn":
                try:
                    Log.info("powering-off...")
                    task = self.vm_obj.PowerOffVM_Task()
                    WaitForTask(task, self.service_instance)
                    self.vm_obj = self.get_vm()
                    Log.info("powering-off succeded")
                except Exception as e:
                    Log.error("powering-off failed: {0}".format(e))
            else:
                Log.info("virtual machine in not powered-on")

    def destroy(self):
        """ Wrapper to destroy a VM """
        Log.task("destroy virtual machine: {0}".format(self.name))
        Log.info("destroying...")
        self.power_off()
        self.delete()
        Log.info("destroy succeeded")

    def clone_vm(self):
        """ Clone VM from a previously created template,
        template_name == vm_name without last 3 digits """
        Log.subtask("clone virtual machine")
        Log.info("- source: {0}".format(self.template_name))
        Log.info("- destination: {0}".format(self.name))

        template_vm = self.get_vm(isTemplate=True)
        if template_vm:
            self._check_media()

            vm_clone_spec = vim.vm.CloneSpec(
                location=vim.vm.RelocateSpec(
                    datastore=self.datastore,
                    pool=self.resource_pool),
                powerOn=False,
                template=False)

            task = template_vm.CloneVM_Task(
                folder=self.datacenter.vmFolder,
                name=self.name,
                spec=vm_clone_spec)

            try:
                Log.info("cloning...")
                WaitForTask(task)
                self.vm_obj = self.get_vm(isTemplate=False)
                Log.info("cloning succeeded")
            except Exception as e:
                Log.error("cloning failed: {0}".format(e))
        else:
            Log.error("template not found: {0}".format(self.template_name))

    def deploy(self, admin_ip=None):
        """ Wrapper to deploy a VM (slow) """

        Log.task("deploy virtual machine: {0}".format(self.name))
        Log.info("deploying...")

        self.create_vm()
        self._copy_vmdk()
        CloudInit.create_iso(self.role_config, admin_ip)
        CloudInit.push_iso(self.vsphere, self.role_config)
        self.power_on()

        Log.info("deployment succeeded")

    def deploy_from_template(self, create_template=False, admin_ip=None):
        """ Wrapper to deploy a VM from a previously created template (fast) """

        Log.task("deploy virtual machine from template: {0}".format(self.name))
        Log.info("deploying...")

        if create_template:
            self.create_vm_template()

        self.clone_vm()
        CloudInit.create_iso(self.role_config, admin_ip)
        CloudInit.push_iso(self.vsphere, self.role_config)
        self.power_on()

        Log.info("deployment succeeded")


def clean_up(location, path, vsphere=None):
    """
    Remove local directory in /tmp/stack_hash
    or remote directory in deployment dir path
    """

    Log.task("clean-up {0} files".format(location))

    if location == "local":
        p = os.path.dirname(path)
        if os.path.exists(p):
            shutil.rmtree(p)

    if location == "remote":
        Datastore.delete_path(vsphere, path)

    Log.info("cleaning-up succeeded")


def deploy(vsphere, conf):
    """ Deploy VM and VM Templates """
    admin_ip = None
    vm_deploy_dir = conf["parameters"]["vm_deploy_dir"]
    Datastore.create_dir(vsphere, vm_deploy_dir)

    # Clean up local deployment files if previous deployment failed
    clean_up(location="local", path=conf["admin"]["config"]["path"])

    Log.task("create virtual machines role templates")
    for r in ["admin", "master", "worker"]:
        for vm_config in conf[r]["vmguests"]:
            vm = VMachine(vsphere, conf["parameters"],
                          conf[r]["config"], vm_config)
            vm.create_vm_template()
            break

    # Deploy Admin node
    Log.task("deploy admin nodes")
    for vm_config in conf["admin"]["vmguests"]:
        vm = VMachine(vsphere, conf["parameters"],
                      conf["admin"]["config"], vm_config)
        vm.deploy_from_template(create_template=False)

        # Retrieve Admin IP address
        admin_ip = get_vm_ip(vm, timeout=120, sleep=20)
        Log.info("Admin node IP address: {0}".format(admin_ip))

    # Deploy Master and Worker nodes
    for r in ["master", "worker"]:
        Log.task("deploy {0} nodes".format(r))
        for vm_config in conf[r]["vmguests"]:
            vm = VMachine(vsphere, conf["parameters"],
                          conf[r]["config"], vm_config)
            vm.deploy_from_template(create_template=False, admin_ip=admin_ip)

    if conf["parameters"]["media_type"] is not "iso":
        generate_state_file(vsphere, conf)


def destroy(vsphere, conf):
    """ Destroy VM and VM Templates """

    for r in ["admin", "master", "worker"]:
        Log.task("destroy {0} nodes".format(r))
        for vm_config in conf[r]["vmguests"]:
            vm = VMachine(vsphere, conf["parameters"],
                          conf[r]["config"], vm_config)
            vm.destroy()

    Log.task("delete virtual machines role templates")
    for r in ["admin", "master", "worker"]:
        for vm_config in conf[r]["vmguests"]:
            vm = VMachine(vsphere, conf["parameters"],
                          conf[r]["config"], vm_config)
            vm.unregister(isTemplate=True)
            break

    # Clean up the deployment on the cluster
    clean_up(vsphere=vsphere, location="remote", path=conf["parameters"]["vm_deploy_dir"])


def get_vm_ip(vm_obj, timeout, sleep):
    vm_ip = None
    count = timeout
    Log.info("waiting IP address for virtual machine: {0}".format(vm_obj.name))
    while vm_ip is None and count > 0:
        vm_ip = vm_obj.get_ip()
        count -= 5
        time.sleep(sleep)
        if vm_ip:
            return vm_ip
    if vm_ip is None:
        Log.error("no IP address found in {0} seconds".format(timeout))


def generate_state_file(vsphere, conf):
    """ 
    Generate deployment state file
    Print it to output and write it to local files
    """
    Log.task("generate state file")

    state = {}
    state["config"] = conf["parameters"]

    state_filename = "caasp-vmware.state"

    # Add a directory if provided, otherwise current is used
    if conf["parameters"]["state_file_dir"]:
        state_file_dir = conf["parameters"]["state_file_dir"]

        if state_file_dir[-1] != "/":  # Add slash
            state_file_dir = "{0}/".format(state_file_dir)

        state_filename = "{0}{1}".format(state_file_dir, state_filename)

    state_filename_stack = "{0}-{1}".format(
        state_filename, state["config"]["stack_name"])

    for k in ["vc_username", "vc_password"]:
        del state["config"][k]

    state["vmguests"] = []
    for n in ["admin", "master", "worker"]:
        for vm_config in conf[n]["vmguests"]:
            v = VMachine(vsphere, conf["parameters"],
                         conf[n]["config"], vm_config)

            vm_ip = get_vm_ip(v, timeout=120, sleep=2)
            vm_config["publicipv4"] = vm_ip
            vm_config["fqdn"] = socket.getfqdn(vm_ip)
            vm_config["image"] = os.path.splitext(
                os.path.basename(v.media_name))[0]
            vm_config["uuid"] = v.vm_obj.config.uuid

            state["vmguests"].append(vm_config)
            index = state["vmguests"].index(vm_config)
            state["vmguests"][index]["index"] = index

    state_file_json = json.dumps(state, indent=2)
    print("====BEGINING_STATE====")
    print(state_file_json)
    print("====END_STATE====")

    try:
        Log.info("writing state file to: {0}".format(state_filename))
        with open(state_filename, "w", encoding="utf-8") as f:
            f.write(state_file_json)

        Log.info("copying state file to: {0}".format(state_filename_stack))
        shutil.copyfile(state_filename, state_filename_stack)
    except IOError as e:
        Log.error("I/O error: {0}".format(e))

    Log.info("state files successfully created")


def list_images(vsphere, remote_path):
    """ List images (ISO|VMDK) in a datastore directory """
    Log.task("list images in directory: [{0}]{1}".format(
        vsphere.datastore.name, remote_path))

    if Datastore.path_exists(vsphere, remote_path):
        iso = Datastore.list_path(
            vsphere, remote_path, match_pattern=["*.iso"])
        if iso:
            Log.info("available iso:")
            for i in iso:
                Log.info(" - {0}".format(i))

        vmdk = Datastore.list_path(
            vsphere, remote_path, match_pattern=["*.vmdk"])
        if vmdk:
            Log.info("available vmdk:")
            for i in vmdk:
                Log.info(" - {0}".format(i))
    else:
        Log.error("images directory not found")


def push_image(vsphere, src, remote_path):
    """
    Push an image to the datastore
    The source can be a local path of an HTTP URL
    """
    file_name = os.path.basename(src)
    Log.task("push image to the datastore")
    Datastore.upload_file(
        vsphere, src, "{0}{1}".format(remote_path, file_name))


def main():
    args = parse_args()
    options = get_user_opt(args)
    conf = generate_config(options)
    action = conf["parameters"]["action"]
    media_dir = conf["parameters"]["media_dir"]

    vsphere = VSphere(conf["parameters"])

    if action == "deploy":
        deploy(vsphere, conf)
    elif action == "destroy":
        destroy(vsphere, conf)
    elif action == "plan":
        print("PLAN ACTION")
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(conf)
    elif action == "listimages":
        list_images(vsphere, media_dir)
    elif action == "pushimage":
        push_image(vsphere, conf["parameters"]["source_media"], media_dir)


if __name__ == "__main__":
    main()
