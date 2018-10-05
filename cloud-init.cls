#cloud-config

# set locale
locale: en_US.UTF-8

# set timezone
timezone: Europe/Warsaw
#hostname: SET_HOSTNAME

users:
  - default
  - name: root
    lock_passwd: false
    passwd: susetesting
    ssh-authorized-keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC2G7k0zGAjd+0LzhbPcGLkdJrJ/LbLrFxtXe+LPAkrphizfRxdZpSC7Dvr5Vewrkd/kfYObiDc6v23DHxzcilVC2HGLQUNeUer/YE1mL4lnXC1M3cb4eU+vJ/Gyr9XVOOReDRDBCwouaL7IzgYNCsm0O5v2z/w9ugnRLryUY180/oIGeE/aOI1HRh6YOsIn7R3Rv55y8CYSqsbmlHWiDC6iZICZtvYLYmUmCgPX2Fg2eT+aRbAStUcUERm8h246fs1KxywdHHI/6o3E1NNIPIQ0LdzIn5aWvTCd6D511L4rf/k5zbdw/Gql0AygHBR/wnngB5gSDERLKfigzeIlCKf Unsafe Shared Key

# set as admin node
suse_caasp:
  role: cluster
  admin_node: SET_ADMIN_NODE

final_message: "The system is finally up, after $UPTIME seconds"
