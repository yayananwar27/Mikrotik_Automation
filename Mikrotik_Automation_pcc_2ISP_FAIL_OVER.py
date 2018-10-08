import paramiko
import time 
from getpass import getpass
import sys
import os
import re

try:
	print('-------------WELCOME---------------')
	print('AUTOMATION MIKORITIK LOAD BALANCING')
	print('------------PCC METHOD-------------')

	ip_mikrotik = str(input('Masukkan IP mikrotik anda : '))

	ok_connect = []
	print('checking the connection........')
	response = os.system("ping {}".format(ip_mikrotik))
	if response == 0:
		print("\n\n{} Dapat Terhubung \n\n".format(ip_mikrotik))
		ok_connect.append(ip_mikrotik)
	else:
		print("\n\n{} Tidak Dapat Terhubung \n\n".format(ip_mikrotik))

	username = str(input('username : '))
	password = getpass()

	for x in ok_connect:
		ok_connect_str = (x)
		ssh_client = paramiko.SSHClient()
		ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh_client.connect(hostname=ok_connect_str,username=username,password=password)
		
		print('berhasil login ke {}'.format(ok_connect_str))

		wan1 = str(input('Interface ISP 1 : '))
		wan2 = str(input('Interface ISP 2 : '))
		jum_int_cl = int(input('jumlah Interface yang terhubung dengan client : '))
		range_int_cl = range(jum_int_cl)
		list_client = []
		for int_jum in range_int_cl:
			int_ke = int_jum+1
			int_cl = str(input('masukkan interface client {} : '.format(int_ke)))
			list_client.append(int_cl)
#mangle input output 
		configan_input_output = ['ip firewall mangle add chain=input in-interface={} action=mark-connection new-connection-mark=WAN1_conn'.format(wan1),
								'ip firewall mangle add chain=input in-interface={} action=mark-connection new-connection-mark=WAN2_conn'.format(wan2),
								'ip firewall mangle add chain=output connection-mark=WAN1_conn action=mark-routing new-routing-mark=to_WAN1',
								'ip firewall mangle add chain=output connection-mark=WAN2_conn action=mark-routing new-routing-mark=to_WAN2',
								]
		for config_input_output in configan_input_output:
			ssh_client.exec_command(config_input_output)
			time.sleep(1)
		print('config mark connection dan routing berhasil')
#mangle accept
		stdin, stdout, stderr = ssh_client.exec_command('ip address print')
		output_sh_ip = stdout.readlines()
		print_address = str(output_sh_ip)
		address_re1 = re.compile(r'(\w+)\s+(\w+\.\w+\.\w+\.+\w)\s+'+'({})'.format(wan1))
		address_re2 = re.compile(r'(\w+)\s+(\w+\.\w+\.\w+\.+\w)\s+'+'({})'.format(wan2))
		address_dst1 = address_re1.search(print_address)
		address_dst2 = address_re2.search(print_address)
		for list_client_accept in list_client:
			if address_dst1:
				accept_wan1 = address_dst1.group(2)+'/'+address_dst1.group(1)
				config_accept_wan1 = ['ip firewall mangle add action=accept chain=prerouting disabled=no dst-address={}'.format(accept_wan1)+' in-interface={}'.format(list_client_accept)]
				for config_accept_wan1_f in config_accept_wan1:
					ssh_client.exec_command(config_accept_wan1_f)
					time.sleep(1)
			if address_dst2:
				accept_wan2 = address_dst2.group(2)+'/'+address_dst2.group(1)
				config_accept_wan2 = ['ip firewall mangle add action=accept chain=prerouting disabled=no dst-address={}'.format(accept_wan2)+' in-interface={}'.format(list_client_accept)]
				for config_accept_wan2_f in config_accept_wan2:
					ssh_client.exec_command(config_accept_wan2_f)
					time.sleep(1)
			else:
				print('wrong')
		print('config mangle accept dst berhasil')

		for list_client_pcc in list_client:
			configan_pcc = [
							'ip firewall mangle add chain=prerouting dst-address-type=!local in-interface={}'.format(list_client_pcc)+' per-connection-classifier=both-addresses-and-ports:2/0 action=mark-connection new-connection-mark=WAN1_conn passthrough=yes',
							'ip firewall mangle add chain=prerouting dst-address-type=!local in-interface={}'.format(list_client_pcc)+' per-connection-classifier=both-addresses-and-ports:2/1 action=mark-connection new-connection-mark=WAN2_conn passthrough=yes',
							]
			for configan_pcc_conn in configan_pcc:	
				ssh_client.exec_command(configan_pcc_conn)
				time.sleep(1)		
		print('config mangle pcc berhasil')
#mangle mark routing
		for list_client_routing in list_client:
			configan_mark_routing = [
									'ip firewall mangle add chain=prerouting connection-mark=WAN1_conn in-interface={}'.format(list_client_routing)+' action=mark-routing new-routing-mark=to_WAN1',
									'ip firewall mangle add chain=prerouting connection-mark=WAN2_conn in-interface={}'.format(list_client_routing)+' action=mark-routing new-routing-mark=to_WAN2',
									]
			for config_mark_routing in configan_mark_routing:
				ssh_client.exec_command(config_mark_routing)
				time.sleep(1)						
		print('config mark routing berhasil')
#default route
		stdin, stdout, stderr = ssh_client.exec_command('ip arp print')
		output_sh_arp = stdout.readlines()
		print_arp = str(output_sh_arp)
		arp_re1 = re.compile(r'(\w+\.\w+\.\w+\.\w)\s+\w+\W\w+\W\w+\W\w+\W\w+\W\w+\s+'+'{}'.format(wan1))
		arp_re2 = re.compile(r'(\w+\.\w+\.\w+\.\w)\s+\w+\W\w+\W\w+\W\w+\W\w+\W\w+\s+'+'{}'.format(wan2))
		arp_dst1 = arp_re1.search(print_arp)
		arp_dst2 = arp_re2.search(print_arp)
		if arp_dst1:
			gateway1 = ''+arp_dst1.group(1)
			config_arp_wan1 = [
							  'ip route add dst-address=0.0.0.0/0 gateway={} check-gateway=ping routing-mark=to_WAN1'.format(gateway1),
							  ]
			for config_def_wan1_f in config_arp_wan1:
				ssh_client.exec_command(config_def_wan1_f)
				time.sleep(1)
			if arp_dst2:
				gateway2 = ''+arp_dst2.group(1)
				config_arp_wan2 = [
								'ip route add dst-address=0.0.0.0/0 gateway={} check-gateway=ping routing-mark=to_WAN2'.format(gateway2),
								]
				for configan_arp_wan2 in config_arp_wan2:
					ssh_client.exec_command(configan_arp_wan2)
					time.sleep(1)					
		
		if arp_dst2:
			gateway2 = ''+arp_dst2.group(1)
			config_arp_wan2_2 = [
							  'ip route add dst-address=0.0.0.0/0 gateway={} check-gateway=ping distance=2'.format(gateway2),
							  ]
			for config_def_wan2_f in config_arp_wan2_2:
				ssh_client.exec_command(config_def_wan2_f)
				time.sleep(1)		
			if arp_dst1:
				gateway1 = ''+arp_dst1.group(1)
				config_arp_wan1_2 = [
									'ip route add dst-address=0.0.0.0/0 gateway={} check-gateway=ping distance=1'.format(gateway1),
									]
				for config_arp_wan1 in config_arp_wan1_2:
					ssh_client.exec_command(config_arp_wan1)
					time.sleep(1)	
		else:
			print('wrong')
		print('configan default route berhasil')
#nat jaringan 
		config_nat =[
					'ip firewall nat add chain=srcnat action=masquerade out-interface={}'.format(wan1),
					'ip firewall nat add chain=srcnat action=masquerade out-interface={}'.format(wan2),
					]
		for configan_nat in config_nat:
			ssh_client.exec_command(configan_nat)
			time.sleep(1)
		print('Config NAT berhasil melalui 2 isp')


		print('\n\nkonfigurasi selesai\n\n')
		print('Configured by Yayan Anwar')

except KeyboardInterrupt:
    print ("\n\nProgram Cancelled by user, Exiting...\n\n")
    sys.exit()

