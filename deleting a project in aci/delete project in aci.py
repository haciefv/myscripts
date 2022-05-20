import json
import sys
import yaml
import time

try:
    from paramiko import SSHClient, AutoAddPolicy
    from paramiko.auth_handler import AuthenticationException
    from scp import SCPClient, SCPException
except ImportError:
    print('Error: You need install "paramiko" python module!\n    pip install paramiko')
    print('Error: You need install "scp" python module!\n    pip install scp')
    sys.exit(1)


class RemoteClient:
    """Client to interact with a remote host via SSH & SCP."""
    def __init__(self, address, username, password=None, ssh_key=None):
        self.client = None
        self.scp = None
        self.address = address
        self.username = username
        self.password = password
        # self.ssh_key = ssh_key

    def connect(self):
        """Open connection to remote host."""
        try:
            self.client = SSHClient()
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            self.client.connect(
                hostname=self.address, username=self.username,
                password=self.password,  # key_filename=self.ssh_key,
                timeout=10000
            )
            self.scp = SCPClient(self.client.get_transport(), socket_timeout=120.0)

        except AuthenticationException as error:
            print(error)
            raise error

    def disconnect(self):
        """Close SSH connection."""
        self.client.close()
        self.scp.close()

    def _execute_command(self, command):
        """Execute command on remote host."""
        stdin, stdout, stderr = self.client.exec_command(command)
        data = (stdout.read() + stderr.read()).decode('utf-8')
        return data.lower()

    def _node_execute(self, command):
        """Execute command under ACI"""
        try:
            cmd = '. /etc/kolla/admin-openrc.sh && ' \
                  'export OS_USERNAME=admin && ' \
                  'export OS_PASSWORD=qwe123QWE && ' \
                  'openstack --insecure --os-compute-api-version 2.60 {}'.format(command)
            result = self._execute_command(cmd)
            return json.loads(result)
        except json.JSONDecodeError:
            print("An error occurred while executing the command '{}'".format(command))
            sys.exit(1)

    def get_project_id(self, cmd):
        data = self._node_execute('project list -f json')
        for line in data:
            print(line)
            if line['name'] == cmd:
                return line['id']

    def get_network_ids(self, project_id):
        networks_ids = []
        if project_id != '':
            data = self._node_execute('network list --project {} -f json'.format(project_id))
            for line in data:
                networks_ids.append(line['id'])
                print(line)
        print('Saved it: {}'.format(networks_ids))
        return networks_ids

    def get_port_ids(self, networks_ids):
        ports_ids = list()
        data = []
        if networks_ids != '':
            for id in networks_ids:
                data.append(self._node_execute('port list --network {} -f json'.format(id)))
        for line in data:
            print(line)
            for index in line:
                ports_ids.append(index['id'])
        print('Saved it: {}'.format(ports_ids))
        return ports_ids

    def get_security_group_ids(self, project_id):
        group_ids = []
        if project_id != '':
            data = self._node_execute('security group list --project {} -f json'.format(project_id))
            for line in data:
                group_ids.append(line['id'])
                print(line)
            print('Saved it: {}'.format(group_ids))
        return group_ids

    def _node_execute_to_delete(self, command):
        """Execute command under ACI"""
        cmd = '. /etc/kolla/admin-openrc.sh && ' \
              'export OS_USERNAME=admin && ' \
              'export OS_PASSWORD=qwe123QWE && ' \
              'openstack --insecure --os-compute-api-version 2.60 {}'.format(command)

        return self._execute_command(cmd)


    def get_vms_by_project(self, project_id: str):
        data = f'server list --project {project_id} -f json'
        data_new = self._node_execute(data)
        vms_ids = []
        for item in data_new:
            vms_ids.append(item['id'])

        if len(vms_ids) == 0:
            print('No Vms in the project')
            return

        return vms_ids


    def delete_vms_under_prject(self, project_id: str):

        vm_ids = self.get_vms_by_project(project_id)
        if vm_ids is None:
            print('Delete method will skip')
            return None

        for id in vm_ids:
            self._node_execute_to_delete(f'server delete {id}')
            time.sleep(60)

    def delete_all_project(self, group_ids, ports_ids, networks_ids, project_id):
        print('Start to deleting:')
        print('ports:')
        for id in ports_ids:
            self._node_execute_to_delete('port delete {}'.format(id))
            print(id)
        print('networks_ids:')
        for id in networks_ids:
            self._node_execute_to_delete('network delete {}'.format(id))
            print(id)
        print('group_ids:')
        for id in group_ids:
            self._node_execute_to_delete('security group delete {}'.format(id))
            print(id)
        self._node_execute_to_delete('project delete {}'.format(project_id))


def main():
    with open("conf.yml", 'r') as stream:
        data_loaded = yaml.safe_load(stream)

    RC = RemoteClient(data_loaded.get('ip_of_aci'), data_loaded.get('login'), data_loaded.get('password'))
    RC.connect()
    project_id = RC.get_project_id(data_loaded.get('project_name'))
    print('Saved project_id: ', project_id)
    RC.delete_vms_under_prject(project_id=project_id)

    print('Networks: ')
    networks_ids = RC.get_network_ids(project_id)
    print('Ports: ')
    ports_ids = RC.get_port_ids(networks_ids)
    print('Group:')
    group_ids = RC.get_security_group_ids(project_id)

    y = input('Continue? (y/n): ')
    if y=='y':
        RC.delete_all_project(group_ids, ports_ids, networks_ids, project_id)
    else:
        exit()
    RC.disconnect()

if __name__ == "__main__":
    main()
