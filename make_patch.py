#!/usr/bin/python2.6
#-*- coding:utf-8 -*-
import os
import shutil
import click
from subprocess import Popen, PIPE

# make Makefile
makefile_header = '''ARCH=$(shell uname -m)
ifeq ($(ARCH), x86_64)
  VER=x86_64
else
  VER=i686
endif

'''


def run(cmdline, stdin=None):
	if stdin:
		p = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
		p.communicate(stdin)
	else:
		p = Popen(cmdline, stdout=PIPE, stderr=PIPE, close_fds=True, shell=True)
	p.wait()
	
	stdout = ''
	if p.stdout is not None:
		stdout = p.stdout.read()

	stderr = ''
	if p.stderr is not None:
		stderr = p.stderr.read()

	return stdout, stderr

def pipe(cmds):
	stdin, stdout, stderr = None, None, None
	for cmd in cmds:
		stdout, stderr = run(cmd, stdin)
		stdin = stdout

	return stdout, stderr

def encrypt_php(php, dst, filename, samefile_num):
	php_screw = '/usr/bin/php-screw'
	copy_file(php, dst, os.path.basename(php), samefile_num)
	dst_filename = os.path.join(dst, filename)
	if os.path.exists(dst_filename):
		base, ext = os.path.splitext(dst_filename)
		filename = base + str(samefile_num) + ext
	encryptcmd = '%s -o %s %s' %(php_screw, filename, php)
	run(encryptcmd)


def python_model(python, dst, filename, samefile_num):
	name = os.path.basename(python)
	dst_filename = os.path.join(dst, name)
	copy_file(python , dst, name, samefile_num)
	cmd = 'cd %s ;python -c "import %s" ; rm %s' %(dst, name, name)
	run(cmd)


# 过滤po files
#没有po文件的加入到new_files
def filter_pofiles(files):
	is_exist_pofiles = False
	new_files = []
	for file in files:
		base, ext = os.path.splitext(file)
		if ext in ('.po', ):
			is_exist_pofiles = True
			continue
		new_files.append(file)

	if is_exist_pofiles:
		new_files.append('locale/zh_CN.mo')
		new_files.append('locale/en_US.mo')
	return new_files


def mkdir(path):
	if not os.path.exists(path):
		os.mkdir(path)


def is_python(file):
	base, ext = os.path.splitext(file)
	if ext in ('.py', ):
		full_name = base + '.pyc'
		if os.path.exists(full_name): return True
	return False


def is_php(file):
	base, ext = os.path.splitext(file)
	return ext in ('.php', )


def install(fp, filename, dst, backup=True):
	if is_python(dst):  
		filename += 'c'
		dst += 'c'
	#if backup:
	cmd = '\t[ -f %s.bak ] || cp %s %s.bak\n' %(filename, dst, filename)
	fp.write(cmd)
	cmd = '\tcp -f %s %s\n' %(filename, dst)
	fp.write(cmd)
	

def get_service(files):
	services = ('shterm-healthd','shterm-permsrv','shterm-rdpextsrv','postgresql','uwsgi','httpd')
	new_services = []
	for service in services:
		prompt = "using service %s, (y/n) Y " %service
		result = raw_input(prompt)
		if result == 'y':
			new_services.append(service)
		elif result == 'n': pass
		else: print 'enter y or n'
	return new_services



def uninstall(fp, filename, dst, backup=False):
	if is_python(dst):  
		filename += 'c'
		dst += 'c'
	cmd = '\tcat %s.bak > %s\n' %(filename, dst)

	fp.write(cmd)
	

def write_services(fp, services):
	for service in services:
		fp.write('\tservice %s restart\n' % service)


def adjust_dst_filename(filename):
	paths = filename.split(os.sep)
	start = paths[0]
	left = paths[1:]
	
	if start == 'web':
		www = '/var/www/shterm/' 
		filename = os.path.join(www, *tuple(left))
	elif start == 'python':
		shterm = '/usr/lib/python2.6/site-packages/shterm'
		filename = os.path.join(shterm, *tuple(left))
	elif start == 'share':
		share ='/usr/share/shterm'
		filename = os.path.join(share,*tuple(left))
	elif start == 'libexec':
		libexec = '/usr/libexec/shterm'
		filename = os.path.join(libexec, *tuple(left))
	elif start == 'locale':
		if 'zh' in left[0]:
			locale = '/usr/share/locale/zh_CN/LC_MESSAGES/'
		else:
			locale = '/usr/share/locale/en_US/LC_MESSAGES'
		filename = os.path.join(locale, 'shterm.mo')
	elif start == 'api':
		pass	
		# api

	return filename


def copy_file(file, dst, filename, samefile_num):
	dst_filename = os.path.join(dst, filename)
	if os.path.exists(dst_filename):
		base, ext = os.path.splitext(dst_filename)
		filename = base + str(samefile_num) + ext
		dst_filename = os.path.join(dst, filename)
	shutil.copyfile(file, dst_filename)


def copy_file_manager(file, src_dst, branch_patch, filename, samefile_num):
	copy_file(file, src_dst, filename, samefile_num)

	if is_python(file):
		python_model(file, branch_patch, filename, samefile_num)
	elif is_php(file):
		encrypt_php(file, branch_patch, filename, samefile_num)
	else:
		filename = os.path.basename(file)
		copy_file(file, branch_patch, filename, samefile_num)


@click.command()
@click.option("--dst",prompt="input destination address",default='pwd',help="destination address is where you want your patch to place, default is current directory")
@click.option("--patch_name",prompt="input the patch name without branch",help="patch name ")
@click.option("--start_hash",prompt="input start hash number(the old one)",help="hash number is the hash value that where you commit you code  ")
@click.option("--end_hash",prompt="input end hash number(the new one)",default='None', help="end hash number ,can't be empty")
def main(dst,patch_name,start_hash,end_hash):
	if dst.startswith('~') : dst = os.path.expanduser(dst) 
	if dst == 'pwd': dst = os.getcwd()
	print dst
	if not os.path.exists(dst): 
		print "the destination address error,please check" 
		return

	filescmd ="git diff %s | grep diff | grep -v Makefile | awk '{print $3}'" % start_hash
	files = run(filescmd)[0].split('\n')
	if end_hash != 'None':
		filescmd = "git diff %s %s | grep diff | grep -v Makefile | awk '{print $3}'" %(start_hash, end_hash)
		files = run(filescmd)[0].split('\n')
	files = [file[2:] for file in files if file.strip()]
	if not files: 
		print "maybe hash number wrong ,there is no file in patch."
		return
	files = filter_pofiles(files)

	branchcmd = "git branch | grep \\* | awk '{print $2}'"
	branch = run(branchcmd)[0]
	branch = branch.strip()

	dst_start = os.path.join(dst, patch_name + '-' +branch)
	mkdir(dst_start)
	patch_dst = os.path.join(dst_start, 'patch')
	mkdir(patch_dst)
	src_dst = os.path.join(dst_start, 'src')
	mkdir(src_dst)

	branch_patch = os.path.join(patch_dst, patch_name + '-' + branch)
	mkdir(branch_patch)
	for file in files:
		filename = os.path.basename(file)
		if filename == 'null' : continue
		copy_file_manager(file, src_dst, branch_patch, filename, samefile_num)

	services = get_service(files)
	hash_file = os.path.join(branch_patch, 'hash')
	with open(hash_file, 'w') as hf:
		hf.write(end_hash)

	makefile = os.path.join(src_dst, 'Makefile')
	with open(makefile, 'w') as fp:
		fp.write(makefile_header)
		
		# install
		fp.write('install:\n')
		for file in files:
			filename = os.path.basename(file)	
			dst = adjust_dst_filename(file)
			install(fp, filename, dst)
		fp.write('\t@echo done\n')
		write_services(fp, services)

		# uninstall
		fp.write('uninstall:\n')
		for file in files:
			filename = os.path.basename(file)	
			dst = adjust_dst_filename(file)
			uninstall(fp, filename, dst)
		fp.write('\t@echo done\n')
		write_services(fp, services)

	shutil.copyfile(makefile, os.path.join(branch_patch, 'Makefile'))
	tar_name = branch_patch + ".tar.bz2"
	tarcmd = "cd %s ;tar jcvf %s %s" %(patch_dst,tar_name, patch_name + '-' + branch)
	run(tarcmd)
	print "excute complete"

if __name__ == '__main__':
	main()
