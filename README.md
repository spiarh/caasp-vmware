# CaaSP VMware

Deploy CaaSP on VMware vSphere

**WORK IN PROGRESS**

**WORK IN PROGRESS**

**WORK IN PROGRESS**

TODO:

* [enhancement] Change project structure
* [enhancement] Improve outputs (color, formating and duration)
* [documentation] List vcenter privileges required for a user

*Notes:*

The default configuration file is **caasp-vmware.yaml**

The command line arguments takes precedence on config file options.

Memory must always be expressed in **mega-bytes**.

# Requirements

The credentials can be exported if you are using *python virtualenv*:

```console
$ export VC_HOST=vcenter.example.com
$ export VC_USERNAME=user@vcenter.example.com
$ export VC_PASSWORD=password
```

Or set into file if you are using the *Docker image*:

```console
$ cat > ./vsphere-secrets <<EOF
VC_HOST=vcenter.example.com
VC_USERNAME=user@vcenter.example.com
VC_PASSWORD=password
EOF
```

`genisoimage` must be installed where the script is running.

## Usage

### Docker

Build the docker image and create an alias so we can call it
directly from command line, see examples below.

```console
$ sudo docker build -t pyvomi .

$ alias pyvomi="sudo docker run -ti --rm --name pyvomi \
    --env-file ./vsphere-secrets \
    -v "$PWD":/app \
    pyvomi "
```

### Python virtualenv

```console
$ pip install -r requirements.txt
```

## Options

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`N/A` | --var-file | all | Deployment customization file | `./caasp-vmware.yaml`
`N/A` | --show-all | status | Show every VMs on the cluster | `N/A`

*misc*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`stack_name` | --stack-name | deploy,destroy | Name of the stack  | `None`
`guest_id` | --guest-id | deploy | Guest operating system identifier | `None`
`state_file_dir` | --state-file-dir | deploy | Directory used to save state file | `Current dir`

*media*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`media_type` | --media-type | deploy | Choose installation media type | `vmdk`
`media` | --media | deploy | Installation media name | `None`
`media_dir` | --media-dir | deploy,listimages,pushimage | Media directory on the datastore | `None`
`source_media` | --source-media | pushimage |  Source media to upload to the remote media directory ( local or http) | `None`

*cloud-init*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`admin_cloud_init` | --admin-cloud-init | deploy | Local cloud-init config file for the admin node | `cloud-init.adm`
`node_cloud_init` | --node-cloud-init | deploy | Local cloud-init config file for the master/worker nodes | `cloud-init.cls`

*vCenter*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`vc_port` | --vc-port | all | vCenter host port | `443`
`vc_insecure` | --vc-insecure | all | Disable certificate verification | `False`
`vc_datacenter` | --vc-datacenter | all | Datacenter to use | `None`
`vc_datastore` | --vc-datastore | all | Datastore to use | `None`
`vc_network` | --vc-network | deploy | Network for the virtual machines | `VM Network`
`vc_resource_pool` | --vc-resource-pool | Resource pool for the virtual machines | `None`

*admin*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`admin_prefix` | --admin-prefix | deploy,destroy |  Admin node name prefix | `caasp-admin`
`admin_ram` | --admin-ram | deploy | Admin RAM | `8192`
`admin_cpu` | --admin-cpi | deploy | Admin CPUs | `2`

*masters*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`master_count` | --master-count | deploy,destroy | Number of masters |`1`
`master_prefix` | --master-prefix | deploy,destroy | Master node name prefix | `caasp-master`
`master_ram` | --master-ram | deploy | Master RAM |`4096`
`master_cpu` | --master-cpu | deploy | Master CPU |`2`

*workers*

File option | CLI option | Action | Description | Default
------------|------------|--------|-------------|--------
`worker_count` | --worker-count | deploy,destroy | Number of workers |`2`
`worker_prefix` | --worker-prefix | deploy,destroy | Worker node name prefix | `caasp-worker`
`worker_ram` | --worker-ram | deploy | Worker RAM |`2048`
`worker_cpu` | --worker-cpu | deploy | Worker CPU |`1`

## CLI Example

### deploy

We assume you are working in the repository directory.

Deploy with the default parameters:

```console
$ pyvomi caasp-vmware.py deploy --stack-name example
```

Deploy 3 masters, 10 workers, override default RAM and CPU for workers:

```console
$ pyvomi caasp-vmware.py deploy --stack-name example \
   --master-count 3 \
   --worker-count 10 \
   --worker-ram 16384 \
   --worker-cpu 4
```

### status

Show the status of a deployed stack:

```console
$ pyvomi caasp-vmware.py status --stack-name example
```

Show the status of every virtual machines in the VMware cluster:

```console
$ pyvomi caasp-vmware.py status --show-all
```

### destroy

Destroy the deployment:

```console
$ pyvomi caasp-vmware.py destroy --stack-name example
```

### image management

List images in the image directory *media_dir*

```console
$ pyvomi caasp-vmware.py listimages
```

Push and image to *media_dir* from a remote location"

```console
$ pyvomi caasp-vmware.py pushimage \
    --source-media https://URL/SUSE-CaaS-Platform-4.0-for-VMware.x86_64-4.0.0-GM.vmdk
```

Push and image to *media_dir* from a local file:

```console
$ pyvomi caasp-vmware.py pushimage \
    --source-media /home/user/images/SUSE-CaaS-Platform-4.0-for-VMware.x86_64-4.0.0-GM.vmdk
```

Delete an image from *media_dir*:

```console
$ pyvomi caasp-vmware.py deleteimage \
    --media-dir image_dir \
    --media SUSE-CaaS-Platform-3.0-for-VMware.x86_64-3.0.0-GM.vmdk
```

## CLI syntax

```console
$ pyvomi caasp-vmware.py --help
usage: caasp-vmware.py [-h] [--var-file [VAR_FILE]]
                       [--stack-name [STACK_NAME]] [--guest-id [GUEST_ID]]
                       [--state-file-dir [STATE_FILE_DIR]]
                       [--media-type [{iso,vmdk}]] [--media [MEDIA]]
                       [--media-dir [MEDIA_DIR]]
                       [--source-media [SOURCE_MEDIA]]
                       [--admin-cloud-init [ADMIN_CLOUD_INIT]]
                       [--node-cloud-init [NODE_CLOUD_INIT]]
                       [--vc-host [VC_HOST]] [--vc-port [VC_PORT]]
                       [--vc-username [VC_USERNAME]]
                       [--vc-password [VC_PASSWORD]]
                       [--vc-insecure [{True,False}]]
                       [--vc-datacenter [VC_DATACENTER]]
                       [--vc-datastore [VC_DATASTORE]]
                       [--vc-network [VC_NETWORK]]
                       [--vc-resource-pool [VC_RESOURCE_POOL]]
                       [--admin-prefix [ADMIN_PREFIX]]
                       [--admin-cpu [ADMIN_CPU]] [--admin-ram [ADMIN_RAM]]
                       [--master-count [MASTER_COUNT]]
                       [--master-prefix [MASTER_PREFIX]]
                       [--master-cpu [MASTER_CPU]] [--master-ram [MASTER_RAM]]
                       [--worker-count [WORKER_COUNT]]
                       [--worker-prefix [WORKER_PREFIX]]
                       [--worker-cpu [WORKER_CPU]] [--worker-ram [WORKER_RAM]]
                       [{plan,deploy,destroy,status,listimages,pushimage,deleteimage}]

Process args

positional arguments:
  {plan,deploy,destroy,status,listimages,pushimage,deleteimage}
                        Execution command

optional arguments:
  -h, --help            show this help message and exit
  --var-file [VAR_FILE]
                        Deployment customization file
  --stack-name [STACK_NAME]
                        Name of the stack
  --guest-id [GUEST_ID]
                        Guest operating system identifier
  --state-file-dir [STATE_FILE_DIR]
                        Directory used to save state file
  --media-type [{iso,vmdk}]
                        Choose installation media type
  --media [MEDIA]       Installation media name
  --media-dir [MEDIA_DIR]
                        Media directory on the datastore
  --source-media [SOURCE_MEDIA]
                        Source media to upload to the remote media directory
  --admin-cloud-init [ADMIN_CLOUD_INIT]
                        Path to the cloud-init config file for the admin node
  --node-cloud-init [NODE_CLOUD_INIT]
                        Path to the cloud-init config file for the master and
                        worker nodes
  --vc-host [VC_HOST]   vCenter host to connect to
  --vc-port [VC_PORT]   vCenter host port
  --vc-username [VC_USERNAME]
                        vCenter username
  --vc-password [VC_PASSWORD]
                        vCenter password
  --vc-insecure [{True,False}]
                        Disable certificate verification
  --vc-datacenter [VC_DATACENTER]
                        Datacenter to use
  --vc-datastore [VC_DATASTORE]
                        Datastore to use
  --vc-network [VC_NETWORK]
                        Network for the virtual machines
  --vc-resource-pool [VC_RESOURCE_POOL]
                        Resource pool for the virtual machines
  --admin-prefix [ADMIN_PREFIX]
                        Admin node name prefix
  --admin-cpu [ADMIN_CPU]
                        Admin CPUs
  --admin-ram [ADMIN_RAM]
                        Admin RAM
  --master-count [MASTER_COUNT]
                        Number of masters
  --master-prefix [MASTER_PREFIX]
                        Master node name prefix
  --master-cpu [MASTER_CPU]
                        Master CPUs
  --master-ram [MASTER_RAM]
                        Master RAM
  --worker-count [WORKER_COUNT]
                        Number of workers
  --worker-prefix [WORKER_PREFIX]
                        Worker node name prefix
  --worker-cpu [WORKER_CPU]
                        Worker CPUs
  --worker-ram [WORKER_RAM]
                        Worker RAM
  --show-all            Show every VMs on the cluster, can take long time
```
