import json
import os
import sys
import yaml
from datetime import datetime

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
        self.ssh_key = ssh_key

    def connect(self):
        """Open connection to remote host."""
        try:
            self.client = SSHClient()
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            self.client.connect(
                hostname=self.address, username=self.username,
                password=self.password,
                key_filename=self.ssh_key,
                timeout=10000
            )
            self.scp = SCPClient(self.client.get_transport(), progress=self.progress)
            print('Connected!')

        except AuthenticationException as error:
            print(
                f"Authentication failed: did you remember to create an SSH key? {error}"
            )
            raise error

    def disconnect(self):
        """Close SSH connection."""
        self.client.close()
        self.scp.close()
        print('Closed the connection')

    def progress(self, filename, size, get):
        if size == get:
            print('Download finished')
            print('Total size:', size, 'get:', get)
        else:
            print("%s\'s progress: %.2f%%   \r" % (filename, float(get) / float(size) * 100))


    def ssh_execute_command(self, command):
        """Execute command on remote host."""
        ssh_stdin, ssh_stdout, ssh_stderr = self.client.exec_command(command)
        ssh_stdout.channel.recv_exit_status()
        response = ssh_stdout.readlines()
        for line in response:
            if line:
                print(f"INPUT: {command} | OUTPUT: {line}")


class ConnectToAci(RemoteClient):
    def _execute_command(self, command):
        """Execute command on remote host."""
        ssh_stdin, ssh_stdout, ssh_stderr = self.client.exec_command(command)
        data = (ssh_stdout.read() + ssh_stderr.read()).decode('utf-8')
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
        print('Getting project id: ')
        data = self._node_execute('project list -f json')
        for line in data:
            print(line)
            if line['name'] == cmd:
                return line['id']

    def get_dict_vm_ip(self, project_id):
        print('Getting vms in the project: ')
        data = self._node_execute('server list --project {} -f json'.format(project_id))
        for dicts in data:
            if dicts['status'] == 'active':
                dicts['networks'] = dicts['networks'].split(';')
                for item in dicts['networks']:
                    # вырезаем все айпишники кроме публичного
                    if item.find('public=') != -1:
                        dicts['networks'] = item.replace('public=', '').replace(' ','')
        return data


with open("conf.yml", 'r') as stream:
    data_loaded = yaml.safe_load(stream)

RCACI = ConnectToAci(data_loaded.get('ip_of_aci'), data_loaded.get('login'), data_loaded.get('password'))
RCACI.connect()
project_id = RCACI.get_project_id(data_loaded.get('project_name'))
dict_name_pub_IP = RCACI.get_dict_vm_ip(project_id)
RCACI.disconnect()


def create_folder(name: str):
    def new_folder(root_folder: str, name: str):
        folder = root_folder + name + str(datetime.strftime(datetime.now(), "-%Y-%m-%d_%H-%M-%S"))
        os.mkdir(folder)
        return folder

    if os.path.exists("logs"):
        return new_folder('logs\\', name)

    os.mkdir('logs')
    return new_folder('logs\\', name)


def get_logs1(dictt: dict, file_and_folder_name: str):
    folder = create_folder(dictt['name']+'-IP'+dictt['networks'])
    RC = RemoteClient(address=dictt['networks'], username='centos', password=None, ssh_key='./ks/default.key')
    RC.connect()
    try:
        RC.ssh_execute_command(f'sudo cp /var/log/{file_and_folder_name}/{file_and_folder_name}.log /home/centos && ls')
        print('started to download:', dictt['name'])
        RC.scp.get(f'/home/centos/{file_and_folder_name}.log', folder)
        RC.ssh_execute_command(f'rm {file_and_folder_name}.log && ls')
    except:
        print('Did not find runvm-agent.log in the /home/centos folder, check manually')
    RC.disconnect()


for dictt in dict_name_pub_IP:

    if dictt['name'].find('agent-gateway') != -1 or dictt['name'].find('agent-runner') != -1 or dictt['name'].find('agent-backuper') != -1:
        get_logs1(dictt, 'runvm-agent')

    elif dictt['name'].find('controller') != -1:
        get_logs1(dictt, 'runvm-controller')

    elif dictt['name'].find('core-dump-server') != -1:
        get_logs1(dictt, 'core-dump-server')