#!/usr/bin/python3.9

import asyncio
import logging

from datetime import datetime,timedelta
from pathlib import Path

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers import date

_app_state={}

def wipedir(dirpath):
	# TODO: Try a different approach for recursive deletions, DO NOT use shutil or subprocess
	for fse in dirpath.iterdir():
		if fse.is_file():
			fse.unlink()
		if fse.is_dir():
			wipedir(fse)
	dirpath.rmdir()

def shred_em(filepath):
	if not filepath.exists():
		logging.info(f"#ttl #end #err {str(filepath)}")
		return

	if filepath.is_file():
		filepath.unlink()

	if filepath.is_dir():
		wipedir(filepath)

	logging.info(f"#ttl #end #ok {str(filepath)}")

def sched_addpath(filepath,ttl):
	jid=str(filepath.resolve())
	if not _app_state["scheduler"].get_job(jid)==None:
		logging.error(f"#ttl #add #err {str(filepath)}")
		return False

	date_target=datetime.now()+timedelta(hours=ttl)

	_app_state["scheduler"].add_job(func=lambda:shred_em(filepath),trigger=date.DateTrigger(date_target),id=jid)
	logging.info(f"#ttl #add #ok {str(filepath)}")

	return True

def shced_delpath(filepath):
	jid=str(filepath.resolve())
	job=_app_state["scheduler"].get_job(jid)
	if job==None:
		logging.error(f"#ttl #del #err {str(filepath)}")
		return False

	job.remove()
	logging.info(f"#ttl #del #ok {str(filepath)}")
	return True

async def http_handler_status(request):
	return web.json_response({"status":200},status=200)

async def http_handler_getlist(request):
	fse_list=[]
	for job in iter(_app_state["scheduler"].get_jobs()):
		fse_list.append({"path":job.id,"eol":str(job.trigger.run_date)})

	return web.json_response({"status":200,"qtty":len(fse_list),"list":fse_list},status=200)

async def http_handler_addpath(request):

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
		ok=sched_addpath(fse,ttl)
		if ok:
			jres={"status":200}
		if not ok:
			jres={"status":400,"msg":"The path has already been added"}

	return web.json_response(jres,status=jres["status"])

async def http_handler_delpath(request):

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
		ok=shced_delpath(fse)
		if ok:
			jres={"status":200}
		if not ok:
			jres={"status":400,"msg":"The path was never added"}

	return web.json_response(jres,status=jres["status"])

async def build_app():
	app=web.Application()
	app.add_routes([
		web.get("/",http_handler_status),
		web.get("/getlist",http_handler_getlist),
		web.post("/addpath",http_handler_addpath),
		web.delete("/delpath",http_handler_delpath),
	])
	return app

if __name__=="__main__":

	import sys

	app_path=Path(sys.argv[0])
	if not len(sys.argv)==3:
		print(f"\nJUDGEMENT DAY\n\nUsage:\n\n$ {app_path.name} Port BaseDir\n\nPort = The port to use\nBaseDir = The base directory that this program is allowed to work on\n\nAbout the BaseDir argument:\n- The base directory path cannot be the same as the program's directory\n- The program's directory cannot be one of the base directory's children\n\nWritten by Carlos Alberto González Hernández\nVersion: 2023-06-07\n")
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
