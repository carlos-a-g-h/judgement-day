#!/usr/bin/python3.9

# import asyncio
import logging

from datetime import datetime,timedelta
from pathlib import Path
from typing import Optional

from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers import date

_app_state={}

def wipedir_loop(dirpath:Path)->list:
	list_paths=[]
	for fse in iter(dirpath.iterdir()):
		if not fse.exists():
			continue
		if fse.is_file():
			fse.unlink()
		if fse.is_dir():
			list_paths.append(fse)

	return list_paths

def wipedir(dirpath:Path):
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

def sched_brand(filepath:Path,ttl:int)->bool:
	jid=str(filepath.resolve())
	if _app_state["scheduler"].get_job(jid) is not None:
		logging.error(f"#brand #err {str(filepath)}")
		return False

	date_target=datetime.now()+timedelta(hours=ttl)

	_app_state["scheduler"].add_job(
		func=lambda:terminate(filepath),
		trigger=date.DateTrigger(date_target),id=jid
	)
	logging.info(f"#brand #ok {str(filepath)}")

	return True

def sched_absolve(filepath:Path)->bool:
	jid=str(filepath.resolve())
	job=_app_state["scheduler"].get_job(jid)
	if job is None:
		logging.error(f"#absolve #err {str(filepath)}")
		return False

	job.remove()
	logging.info(f"#absolve #ok {str(filepath)}")
	return True

def sched_amnesty()->bool:
	no_jobs=(len(_app_state["scheduler"].get_jobs())==0)
	if no_jobs:
		logging.error("#amnesty #err")
		return False

	_app_state["scheduler"].remove_all_jobs()
	logging.error("#amnesty #ok")
	return True

async def http_handler_status(request)->web.json_response:
	return web.json_response({"status":200},status=200)

async def http_handler_cell(request)->web.json_response:
	fse_list=[]
	for job in iter(_app_state["scheduler"].get_jobs()):
		fse_list.append({"path":job.id,"eol":str(job.trigger.run_date)})

	return web.json_response({"status":200,"qtty":len(fse_list),"list":fse_list},status=200)

async def http_handler_brand(request)->web.json_response:
	wutt=False
	if not request.headers.get("content-type")=="application/json":
		wutt=True
		jres={
			"status":415,
			"msg":"Expected application/json"
		}

	if (not wutt):
		try:
			data_in=await request.json()
		except Exception as exc:
			wutt=True
			jres={
				"status":406,
				"msg":f"{exc} (The data is not a valid JSON)"
			}

	if (not wutt):
		fse=Path(data_in.get("path"))
		ttl=int(data_in.get("ttl"))
		if ttl>0:
			wutt=True
			jres={
				"status":400,
				"msg":"Either some fileds are missing or the values provided are not correct"
			}

	if not wutt:
		if not fse.exists():
			wutt=True
			jres={
				"status":400,
				"msg":"The target path does not exist"
			}

	if not wutt:
		if fse.resolve()==_app_state["basedir"]:
			wutt=True
			jres={
				"status":400,
				"msg":"The target path cannot match the base directory"
			}

	if not wutt:
		if not fse.resolve().is_relative_to(_app_state["basedir"]):
			wutt=True
			jres={
				"status":400,
				"msg":"The target path has to be relative to the base directory"
			}

	if not wutt:
		ok=sched_brand(fse,ttl)
		if ok:
			jres={"status":200}
		if not ok:
			jres={
				"status":400,
				"msg":"The path has already been added"
			}

	return web.json_response(jres,status=jres["status"])

async def http_handler_absolve(request)->web.json_response:
	wutt=False
	if not request.headers.get("content-type")=="application/json":
		wutt=True
		jres={
			"status":415,
			"msg":"Expected application/json"
		}

	if not wutt:
		try:
			data_in=await request.json()
		except:
			wutt=True
			jres={
				"status":406,
				"msg":"The data is not a valid JSON"
			}

	if not wutt:
		try:
			fse=Path(data_in.get("path"))
		except:
			wutt=True
			jres={
				"status":400,
				"msg":"Check the 'path' field"
			}

	if not wutt:
		ok=sched_absolve(fse)
		if ok:
			jres={"status":200}
		if not ok:
			jres={
				"status":400,
				"msg":"The path was never added"
			}

	return web.json_response(jres,status=jres["status"])

async def http_handler_amnesty(request)->web.json_response:
	ok=sched_amnesty()
	if ok:
		jres={"status":200}

	if not ok:
		jres={
			"status":400,
			"msg":"The cell is empty"
		}

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
		print(
			"JUDGEMENT DAY" "\n\n"
			"Usage:" "\n\n"
			f"$ {app_path.name} [Port or SocketPath] [BaseDir]" "\n\n"
			"About the binding:\n"
			"- You can either bind to a port or a socket file" "\n"
			"- An integer is directly assumed to be a port, anything else is a socket file" "\n"
			"About the base directory:" "\n"
			"- The base directory path cannot be the same as the program's directory" "\n"
			"- The program's directory cannot be one of the base directory's children" "\n"
		)
		sys.exit(0)

	# Argument 1: Port

	the_port:Optional[int]=None
	the_socket:Optional[str]=None

	argument_one:str=sys.argv[1].strip()
	is_number=argument_one.isdigit()
	if is_number:
		the_port=int(argument_one)

	if not is_number:
		the_socket_path=Path(argument_one)
		if the_socket_path.exists():
			if the_socket_path.is_dir():
				print("Cannot bind to a directory")
				sys.exit(1)

			if the_socket_path.is_file():
				try:
					the_socket_path.unlink()
				except Exception as exc:
					print(
						f"Failed to delete: {the_socket_path}" "\n"
						f"Why: {exc}"
					)
					sys.exit(1)

			if the_socket_path.exists():
				print("Wutt")
				sys.exit(1)

		the_socket=str(the_socket_path)

	# Argument 2: BaseDir

	if (the_port is None) and (the_socket is None):
		print("No port, no socket ???")
		sys.exit(1)

	try:
		the_basedir=Path(sys.argv[2].strip())
	except Exception as exc:
		logging.exception(f"At argument 2: {exc}")
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

	print(
		"JUDGEMENT DAY" "\n"
		f"BaseDir: {the_basedir_abs}"
	)

	# Logging
	logfile=f"{app_path.name}.log"
	with open(logfile,"wt") as log:
		log.write("")

	logging.basicConfig(
		filename=logfile,
		format='[%(levelname) 5s/%(asctime)s] %(name)s %(funcName)s: %(msg)s',
		level=logging.INFO
	)

	# Scheduler
	_app_state.update({"scheduler":AsyncIOScheduler()})
	_app_state["scheduler"].start()

	# Run web application
	web.run_app(build_app(),port=the_port,path=the_socket)
