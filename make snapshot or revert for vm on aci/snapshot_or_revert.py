import json
import sys
import time as time_
from datetime import date
from typing import Any, Callable, Optional

try:
    from paramiko import SSHClient, AutoAddPolicy
    from paramiko.auth_handler import AuthenticationException
    from scp import SCPClient, SCPException
except ImportError:
    print('Error: You need install "paramiko" python module!\n    pip install paramiko')
    print('Error: You need install "scp" python module!\n    pip install scp')
    sys.exit(1)
import argparse


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
            self.scp = SCPClient(self.client.get_transport())
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


class ConnectToAci(RemoteClient):

    def _execute_command(self, command):
        """Execute command on remote host."""
        ssh_stdin, ssh_stdout, ssh_stderr = self.client.exec_command(command)
        data = (ssh_stdout.read() + ssh_stderr.read()).decode('utf-8')
        return data.lower()

    def _node_execute(self, command):
        """Execute command under ACI"""
        try:
            result = self._execute_command(command)
            return json.loads(result)
        except json.JSONDecodeError:
            print("An error occurred while executing the command '{}'".format(command))
            sys.exit(1)

    def get_project_info(self, vm_name: str):
        print('Getting vm info: ')
        data = self._node_execute(f'vinfra service compute server show "{vm_name}" -f json')
        return data

    def get_vm_status_info(self, vm_name: str) -> Optional[int]:
        print('Getting vm status info:')
        data = self._node_execute(f'vinfra service compute server show "{vm_name}" -f json')
        print('status: ', data['status'], ' | ', 'task_state: ', data['task_state'])
        if data['task_state'] is not None or data['task_state'] == 'powering-on' or data['task_state'] == 'powering-off':
            return 2
        elif data['task_state'] is None and data['status'] == 'shutoff':
            return 0
        elif data['task_state'] is None and data['status'] == 'active':
            return 1

    def check_volume(self, id: str) -> bool:
        info = self._node_execute(f'vinfra service compute volume show {id} -f json')
        name = info['name']
        if name.find('cd/dvd') != -1:
            return False
        return True

    def do_snapshot(self, data):

        def get_snapshot_info(id: str):
            info = self._node_execute(f'vinfra service compute volume snapshot show {id} -f json')
            if info['status'] == 'available':
                return 1
            return 2

        i = 0
        print(f'Will create snapshots for {data["volumes"]}')
        for volume in data['volumes']:
            snapshot_name = str(date.today()) + '-' + str(i)
            if self.check_volume(volume["id"]):
                volume_name= self._node_execute(f'vinfra service compute volume show {volume["id"]} -f json')['name']
                volume_name = volume_name+ ' - ' + snapshot_name
                snapshot = self._node_execute(f'vinfra service compute volume snapshot create "{volume_name}" --volume {volume["id"]} -f json')
                if snapshot['status'] == 'creating':
                    if self.wait(get_snapshot_info, snapshot['id']):
                        print(f'Snapshot {snapshot_name} created for volume {volume["id"]}')
            else:
                print(f'Will not create snapshot for {volume["id"]} it is CD\\DVD appliance')

            i += 1

    def stop_vm(self, vm_name: str):
        vm_info = self.get_vm_status_info(vm_name)
        # vm_infa can be 1 or 0 , 1 is running state , 0 stopped

        def turn_off_vm():
            print(f'Started to turn-off vm {vm_name}')
            return self._node_execute(f'vinfra service compute server stop "{vm_name}" -f json')

        if vm_info == 0:
            print('The vm already stopped.')
            return True
        elif vm_info == 2:
            print('Waiting while vm stopping')
            self.wait(self.get_vm_status_info, vm_name)
        elif vm_info == 1:
            turn_off_vm()
            if self.wait(self.get_vm_status_info, vm_name):
                print('turn-off completed')

    def start_vm(self, vm_name: str):
        print(f'Started to turn-on vm {vm_name}')
        vm_info = self.get_vm_status_info(vm_name=vm_name)

        def turn_on_vm():
            self._node_execute(f'vinfra service compute server start "{vm_name}" -f json')

        if vm_info == 1:
            print('The vm already started.')
            return True
        elif vm_info == 2:
            print('Waiting while vm starting')
            self.wait(self.get_vm_status_info, vm_name)
        elif vm_info == 0:
            turn_on_vm()
            if self.wait(self.get_vm_status_info, vm_name):
                print('turn-on completed')

    def do_revert(self, data: dict):
        last_snapshot_id_for_all_volumes = []
        volume_list = data['volumes']
        for volume in volume_list:
            if self.check_volume(volume["id"]):
                snapshots_dict = self._node_execute(f'vinfra service compute volume snapshot list --volume {volume["id"]} -f json')
                if int(len(snapshots_dict)) > 0:
                    last_snapshot_id_for_all_volumes.append(snapshots_dict[0]['id'])
                    print(f'snapshot list by volume id {volume["id"]}: \n', snapshots_dict)
                else:
                    print(f'No snapshot for volume {volume["id"]}')
        #revert to last snapshot
        if int(len(last_snapshot_id_for_all_volumes)) == 0:
            print('No snapshots')
            exit()

        for id in last_snapshot_id_for_all_volumes:
            revert = self._node_execute(f'vinfra service compute volume snapshot revert {id} -f json')
            print(revert)

    def list_of_snapshots(self, data: dict):
        volume_list = data['volumes']
        for volume in volume_list:
            if self.check_volume(volume["id"]):
                list_snapshot = self._node_execute(f'vinfra service compute volume snapshot list --volume {volume["id"]} -f json')
                print(f'snapshot list by volume id {volume["id"]}: \n', list_snapshot)
        return list_snapshot

    def delete_snapshot(self,data: dict):

        volume_list = data['volumes']

        def collect_every_snapshot_vm(volume_list: list):
            list_snapshot = []
            for volume in volume_list:
                if self.check_volume(volume["id"]):
                    data = self._node_execute(f'vinfra service compute volume snapshot list --volume {volume["id"]} -f json')
                    for item in data:
                        list_snapshot.append(item['id'])
            return list_snapshot

        list_snapshot = collect_every_snapshot_vm(volume_list)
        print(list_snapshot)
        r = input('can start to delete (y/n)?: ',)
        if r == 'y':
            for snapshot in list_snapshot:
                self._node_execute(f'vinfra service compute volume snapshot delete {snapshot} -f json')
        else:
            print('Deleting canceled')

    def wait(self, something: Callable[[], Optional[Any]], *args, **kwargs):
        started = time_.time()
        while time_.time() - started < 60:
            time_.sleep(30)
            if something(*args,**kwargs) == 2:
                continue
            else:
                return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Snapshot and Revert VM',
                                     usage='''\
                                snapshot_or_revert.py --list - List of all snapshots 
                                --snap - will create snapshot
                                --revert - will revert on the last snapshot
                                --delete - will delete snapshot
 ''', )
    parser.add_argument('--list', help='Lists snapshots for every VM', action='store_true')
    parser.add_argument('--revert', help='Revert to snapshot', action='store_true')
    parser.add_argument('--delete', help='Deletes snapshot', action='store_true')
    parser.add_argument('--snap', help='Create a snapshot', action='store_true')

    args = parser.parse_args()


    '''
        Оригинал
        RCACI = ConnectToAci(address='10.137.0.2', username='root', password='qwe123QWE')
        RCACI.connect()
        vm_name = 'Global Storage'
    '''

    RCACI = ConnectToAci(address='10.137.0.2', username='root', password='qwe123QWE')
    RCACI.connect()
    vm_name = 'Global Storage'
    vm_info = RCACI.get_project_info(vm_name)


    if args.snap:
        RCACI.do_snapshot(vm_info)

    if args.revert:
        RCACI.stop_vm(vm_name)
        RCACI.do_revert(vm_info)
        RCACI.start_vm(vm_name)

    if args.list:
        RCACI.list_of_snapshots(vm_info)
        # /mnt/vstorage/vols/acronis-backup/storage/999#362/1

    if args.delete:
        RCACI.delete_snapshot(vm_info)

    RCACI.disconnect()


