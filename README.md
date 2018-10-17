# CaaSP VMware

Deploy CaaSP on VMware vSphere

**WORK IN PROGRESS**

**WORK IN PROGRESS**

**WORK IN PROGRESS**

TODO:

* [enhancement] Create plan action to check the deployment before actually deploy
* [enhancement] Change project structure
* [enhancement] Improve outputs (color, formating and duration)
* [documentation] Improve Documentation
* [documentation] List vcenter privileges required for a user



# Requirements

The credentials can be exported

```
VC_HOST=vcenter.example.com
VC_USERNAME=user@vcenter.example.com
VC_PASSWORD=password
```

# Docker

```console
$ sudo docker build -t pyvomi .

$ alias pyvomi="sudo docker run -ti --rm --name pyvomi \
    --env-file ./vsphere-secrets \
    -v "$PWD":/app \
    pyvomi "
```

# Usage

```
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
                       [--master_count [MASTER_COUNT]]
                       [--master-prefix [MASTER_PREFIX]]
                       [--master-cpu [MASTER_CPU]] [--master-ram [MASTER_RAM]]
                       [--worker_count [WORKER_COUNT]]
                       [--worker-prefix [WORKER_PREFIX]]
                       [--worker-cpu [WORKER_CPU]] [--worker-ram [WORKER_RAM]]
                       [{plan,deploy,destroy,listimages,pushimage}]

Process args

positional arguments:
  {plan,deploy,destroy,listimages,pushimage}
                        Execution command

optional arguments:
  -h, --help            show this help message and exit
  --var-file [VAR_FILE]
                        Deployment customization file
  --stack-name [STACK_NAME]
                        Name of the stack to deploy
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
                        Datacenter where to deploy the virtual machines
  --vc-datastore [VC_DATASTORE]
                        Datastore where to store the virtual machines
  --vc-network [VC_NETWORK]
                        Network for the virtual machines
  --vc-resource-pool [VC_RESOURCE_POOL]
                        Resource pool where to deploy the virtual machines
  --admin-prefix [ADMIN_PREFIX]
                        Admin node name prefix
  --admin-cpu [ADMIN_CPU]
                        Admin CPUs
  --admin-ram [ADMIN_RAM]
                        Admin RAM
  --master_count [MASTER_COUNT]
                        Number of masters to deploy
  --master-prefix [MASTER_PREFIX]
                        Master node name prefix
  --master-cpu [MASTER_CPU]
                        Master CPUs
  --master-ram [MASTER_RAM]
                        Master RAM
  --worker_count [WORKER_COUNT]
                        Number of workers to deploy
  --worker-prefix [WORKER_PREFIX]
                        Worker node name prefix
  --worker-cpu [WORKER_CPU]
                        Worker CPUs
  --worker-ram [WORKER_RAM]
                        Worker RAM
```












