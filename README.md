# Judgement Day

## What is this ???

Judgement Day is a scheduler service that deletes files and directories after a certain period of time passes

Although the program is a web server, it is meant to run locally

## Usage

```
# jday [Port or Socket] [BaseDir]
```

`Port` → The port to use

`Socket` → A socket file to use

`BaseDir` → The base directory that this program is allowed to work on

About binding with `Port` or `Socket`:
- You can either bind to a port or a socket file
- An integer is directly assumed to be a port, anything else is a socket file

About the `BaseDir` argument: 
- The base directory path cannot be the same as the program's directory
- The program's directory cannot be one of the base directory's children

All the arguments are mandatory: there are no default values<br>
In case of running without arguments, a quick help text with the usage will be shown

## API

|Name and Description|Method|Route|Data required|Ok Response (200)|Err Response (4xx)|
|-|-|-|-|-|-|
|**Status**<br />Always returns 200|`GET`|`/`||`JSON: {"status":200}`||
|**Brand**<br />Adds a path and a TTL (hours) to the cell|`POST`|`/brand`|`JSON: {"path":(String:Target path),"ttl":(Integer:Hours to live)}`|`JSON: {"status":200}`|`JSON: {"status":4xx,"msg":"Error message"}`|
|**Cell**<br />Shows a list of all the 'branded' paths and the quantity|`GET`|`/cell`||`JSON: {"status":200,"qtty":(Integer:Length of the cell),"list":List(List:Paths and expiration dates)}`|`JSON: {"status":4xx,"msg":"Error message"}`|
|**Absolve**<br />Removes a branded path from the cell|`DELETE`|`/absolve`|`JSON: {"path":(String:Branded path)}`|`JSON: {"status":200}`|`JSON: {"status":4xx,"msg":"Error message"}`|
|**Amnesty**<br />Removes all the branded paths from the cell|`DELETE`|`/amnesty`||`{"status":200}`|`JSON: {"status":4xx,"msg":"Error message"}`|

NOTE about branding (adding): All target paths must be relative to the base directory

## Changelog

### 2024-11-05

- Added unix socket support

### 2023-08-30

- Wiped out directories will no longer leave behind an empty directory

### 2023-06-08

- Attempting to set TTLs smaller than 1 will throw an error

### 2023-06-07

- First Release
