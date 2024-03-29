#!/usr/bin/python3.9

import asyncio
import logging

from datetime import datetime,timedelta
from pathlib import Path

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers import date

_app_state={}

def wipedir_loop(dirpath):
	list_paths=[]
	for fse in iter(dirpath.iterdir()):
		if not fse.exists():
			continue
		if fse.is_file():
			fse.unlink()
		if fse.is_dir():
			list_paths.append(fse)

	return list_paths

def wipedir(dirpath):
	list_paths=[dirpath]
	list_empty=[]
	while len(list_paths)>0:
		path_curr=list_paths.pop()
		list_paths.extend(wipedir_loop(path_curr))
		list_empty.append(path_curr)

	list_empty.reverse()
	for fse in iter(list_empty):
		if not fse.exists():
			continue
		if not fse.is_dir():
			continue
		fse.rmdir()

	if len(list(dirpath.iterdir()))==0:
		dirpath.rmdir()

def terminate(filepath):
	if not filepath.exists():
		logging.error(f"#terminate #err {str(filepath)}")
		return

	if filepath.is_file():
		filepath.unlink()

	if filepath.is_dir():
		wipedir(filepath)

	logging.info(f"#terminate #ok {str(filepath)}")

def sched_brand(filepath,ttl):
	jid=str(filepath.resolve())
	if not _app_state["scheduler"].get_job(jid)==None:
		logging.error(f"#brand #err {str(filepath)}")
		return False

	date_target=datetime.now()+timedelta(hours=ttl)

	_app_state["scheduler"].add_job(func=lambda:terminate(filepath),trigger=date.DateTrigger(date_target),id=jid)
	logging.info(f"#brand #ok {str(filepath)}")

	return True

def sched_absolve(filepath):
	jid=str(filepath.resolve())
	job=_app_state["scheduler"].get_job(jid)
	if job==None:
		logging.error(f"#absolve #err {str(filepath)}")
		return False

	job.remove()
	logging.info(f"#absolve #ok {str(filepath)}")
	return True

def sched_amnesty():
	no_jobs=(len(_app_state["scheduler"].get_jobs())==0)
	if no_jobs:
		logging.error("#amnesty #err")
		return False

	_app_state["scheduler"].remove_all_jobs()
	logging.error("#amnesty #ok")
	return True

async def http_handler_status(request):
	return web.json_response({"status":200},status=200)

async def http_handler_cell(request):
	fse_list=[]
	for job in iter(_app_state["scheduler"].get_jobs()):
		fse_list.append({"path":job.id,"eol":str(job.trigger.run_date)})

	return web.json_response({"status":200,"qtty":len(fse_list),"list":fse_list},status=200)

async def http_handler_brand(request):
	wutt=False
	if not request.headers.get("content-type")=="application/json":
		wutt=True
		jres={"status":415,"msg":"Expected application/json"}

	if (not wutt):
		try:
			data_in=await request.json()
		except:
			wutt=True
			jres={"status":406,"msg":"The data is not a valid JSON"}

	if (not wutt):
		try:
			fse=Path(data_in.get("path"))
			ttl=int(data_in.get("ttl"))
			assert ttl>0
		except:
			wutt=True
			jres={"status":400,"msg":"Either some fileds are missing or the values provided are not correct"}

	if not wutt:
		if not fse.exists():
			wutt=True
			jres={"status":400,"msg":"The target path does not exist"}

	if not wutt:
		if fse.resolve()==_app_state["basedir"]:
			wutt=True
			jres={"status":400,"msg":"The target path cannot match the base directory"}

	if not wutt:
		if not fse.resolve().is_relative_to(_app_state["basedir"]):
			wutt=True
			jres={"status":400,"msg":"The target path has to be relative to the base directory"}

	if not wutt:
		ok=sched_brand(fse,ttl)
		if ok:
			jres={"status":200}
		if not ok:
			jres={"status":400,"msg":"The path has already been added"}

	return web.json_response(jres,status=jres["status"])

async def http_handler_absolve(request):
	wutt=False
	if not request.headers.get("content-type")=="application/json":
		wutt=True
		jres={"status":415,"msg":"Expected application/json"}

	if not wutt:
		try:
			data_in=await request.json()
		except:
			wutt=True
			jres={"status":406,"msg":"The data is not a valid JSON"}

	if not wutt:
		try:
			fse=Path(data_in.get("path"))
		except:
			wutt=True
			jres={"status":400,"msg":"Check the 'path' field"}

	if not wutt:
		ok=sched_absolve(fse)
		if ok:
			jres={"status":200}
		if not ok:
			jres={"status":400,"msg":"The path was never added"}

	return web.json_response(jres,status=jres["status"])

async def http_handler_amnesty(request):
	ok=sched_amnesty()
	if ok:
		jres={"status":200}

	if not ok:
		jres={"status":400,"msg":"The cell is empty"}

	return web.json_response(jres,status=jres["status"])
		
async def build_app():
	app=web.Application()
	app.add_routes([
		web.get("/",http_handler_status),
		web.get("/cell",http_handler_cell),
		web.post("/brand",http_handler_brand),
		web.delete("/absolve",http_handler_absolve),
		web.delete("/amnesty",http_handler_amnesty)
	])
	return app

if __name__=="__main__":

	import sys

	app_path=Path(sys.argv[0])
	if not len(sys.argv)==3:
		print(f"\nJUDGEMENT DAY\n\nUsage:\n\n$ {app_path.name} Port BaseDir\n\nPort = The port to use\nBaseDir = The base directory that this program is allowed to work on\n\nAbout the BaseDir argument:\n- The base directory path cannot be the same as the program's directory\n- The program's directory cannot be one of the base directory's children\n\nWritten by Carlos Alberto González Hernández\nVersion: 2023-06-30\n")
		sys.exit(0)

	# Argument 1: Port
	try:
		the_port=int(sys.argv[1].strip())
	except:
		logging.exception("At argument 1")
		sys.exit(1)

	# Argument 2: BaseDir
	try:
		the_basedir=Path(sys.argv[2].strip())
	except:
		logging.exception("At argument 2")
		sys.exit(1)

	if the_basedir.exists():
		if not the_basedir.is_dir():
			logging.error("The base directory has to be a directory")
			sys.exit(1)

	if not the_basedir.exists():
		the_basedir.mkdir(parents=True,exist_ok=True)

	app_dir=app_path.parent.resolve()
	the_basedir_abs=the_basedir.resolve()
	if the_basedir_abs==app_dir:
		logging.error("The base directory cannot be the same as the program's path")
		sys.exit(1)

	if app_dir.is_relative_to(the_basedir_abs):
		logging.error("The base directory cannot be a parent of the program's path")
		sys.exit(1)

	_app_state.update({"basedir":the_basedir_abs})

	print(f"\nJUDGEMENT DAY\n\nBaseDir:\n  {str(the_basedir_abs)}\n")

	# Logging
	logfile=app_path.name+".log"
	with open(logfile,"wt") as log:
		log.write("")

	logging.basicConfig(filename=logfile,format='[%(levelname) 5s/%(asctime)s] %(name)s %(funcName)s: %(msg)s',level=logging.INFO)

	# Scheduler
	_app_state.update({"scheduler":AsyncIOScheduler()})
	_app_state["scheduler"].start()

	# Run web application
	web.run_app(build_app(),port=the_port)
