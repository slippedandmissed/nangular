#!/usr/bin/python3.9

import argparse
import os
import sys
import shutil
import json
import getpass

parser = argparse.ArgumentParser()
parser.add_argument(
    "name", type=str, help="The name for the node project. This will be the name of the directory created for the backend project.")
parser.add_argument("-d", "--directory", type=str, default=".",
                    help="The directory in which to create the project directory.")
parser.add_argument("-f", "--frontend-name", type=str,
                    default="frontend", help="The name for the angular project.")
parser.add_argument("-l", "--legacy-peer-deps", action="store_true",
                    default=False, help="Use --legacy-peer-deps flag for the frontend.")
parser.add_argument("-H", "--heroku", action="store_true",
                    default=False, help="Make it heroku-ready.")
parser.add_argument("-F", "--force", action="store_true",
                    default=False, help="Force overwrite.")
parser.add_argument("-G", "--git", type=str,
                    default=None, help="URL of git repo (https)")
parser.add_argument("-a", "--author", type=str,
                    default=getpass.getuser(), help="Project author")
parser.add_argument("-L", "--license", type=str,
                    default="ISC", help="Project license")
parser.add_argument("-A", "--api", action="store_true",
                    default=False, help="Set up an API router")
parser.add_argument("-S", "--socketio", action="store_true",
                    default=False, help="Add socketio server")
parser.add_argument("-P", "--port", type=int,
                    default=8000, help="Default port")

args = parser.parse_args()

node_path = os.path.join(os.path.abspath(args.directory), args.name)
angular_path = os.path.join(node_path, args.frontend_name)

print(f"Backend will be created in {node_path}")
print(f"Frontend will be created in {angular_path}")

if os.path.exists(node_path):
    if not args.force and input(f"{node_path} already exists. Are you sure you'd like to overwrite it? (y/N): ").lower() != "y":
        print("Aborting")
        sys.exit()
    else:
        shutil.rmtree(node_path)

os.makedirs(node_path)

os.chdir(node_path)

os.system("git init")

node_version = os.popen("node -v").read()[1:-1]


package_json = {
    "name": args.name,
    "version": "1.0.0",
    "description": "",
    "main": "index.js",
    "engines": {
        "node": node_version
    },
    "scripts": {
        "start": "node index.js",
        "build": f"cd {args.frontend_name} && ng build && cd ..",
        "serve": f"cd {args.frontend_name} && ng serve && cd ..",
        "test": f"cd {args.frontend_name} && ng test && cd .."
    },
    "author": args.author,
    "license": "ISC",
    "dependencies": {}
}

if args.heroku:
    package_json["scripts"]["heroku-postbuild"] = f"cd {args.frontend_name} && npm i{' --legacy-peer-deps' if args.legacy_peer_deps else ''}"

if args.git is not None:
    if args.git.endswith(".git"):
        args.git = args.git[:-4]
    if args.git.endswith("/"):
        args.git = args.git[:-1]
    package_json["repository"] = {
        "type": "git",
        "url": f"git+{args.git}.git"
    }
    package_json["bugs"] = {
        "url": f"{args.git}/issues"
    }
    package_json["homepage"] = f"{args.git}#readme"


with open("package.json", "w") as write:
    write.write(json.dumps(package_json, indent=4))

dependencies = ["express", "dotenv"]
if args.socketio:
    dependencies.append("socketio")

api_code = """
const api = require("./api");
const router = express.Router();
router.use("/api", api);
""" if args.api else ""

socketio_code = """
io.on("connection", (socket) => {
    console.log(`Socket connected: ${socket.id}`);
});
""" if args.socketio else ""

index_js = f"""`use strict`

const express = require("express");
const app = express();
const http = require("http").createServer(app);
{'const io = require("socket.io")(http);' if args.socketio else ""}
require("dotenv").config();

const port = process.env.PORT || {args.port};

app.enable("trust-proxy");
app.use(express.json());
app.use(express.urlencoded({{ extended: true }}));
{api_code}
app.use((req, res, next) => {{
    req.method = "GET";
    next();
}});

const _app_folder = "./{args.frontend_name}/dist/{args.frontend_name}";

app.get("*.*", express.static(_app_folder, {{ maxAge: "1y" }}));
app.all("*", (req, res) => {{
    res.status(200).sendFile("/", {{ root: _app_folder }});
}});
{socketio_code}

http.listen(port, () => {{
    console.log(`Listening on port ${{port}}`);
}});
"""

with open("index.js", "w") as write:
    write.write(index_js)

if args.api:
    os.makedirs("api")
    api_index = """`use strict`

const express = require("express");
const router = express.Router();

module.exports = router;
"""
    with open("./api/index.js", "w") as write:
        write.write(api_index)

for d in dependencies:
    os.system(f"npm i {d}")

gitignore = """# See http://help.github.com/ignore-files/ for more about ignoring files.

.env

# compiled output
/dist
/tmp
/out-tsc
# Only exists if Bazel was run
/bazel-out

# dependencies
/node_modules
package-lock.json

# profiling files
chrome-profiler-events*.json
speed-measure-plugin*.json

# IDEs and editors
/.idea
.project
.classpath
.c9/
*.launch
.settings/
*.sublime-workspace

# IDE - VSCode
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
.history/*

# misc
/.sass-cache
/connect.lock
/coverage
/libpeerconnection.log
npm-debug.log
yarn-error.log
testem.log
/typings

# System Files
.DS_Store
Thumbs.db
"""

with open(".gitignore", "w") as write:
    write.write(gitignore)

with open(".env", "w") as _:
    pass


README = f"""# {args.name}

## How to serve the application
- `npm start` : Serve the application without rebuilding. This will reflect changes in the node server but not the angular app.
- `npm run build` : Rebuild the angular application. This will reflect all changes.
- `npm run test` : Run angular tests.
- `npm run serve` : Just serve the angular app and not the node server. This is purely for testing the UI. Supports hot reloading.
"""

with open("README.md", "w") as write:
    write.write(README)

os.system(f"ng n {args.frontend_name}")
os.chdir(angular_path)
if args.legacy_peer_deps:
    os.system("npm i --legacy-peer-deps")

with open("package.json", "r") as read:
    angular_package_json = json.loads(read.read())

angular_package_json["scripts"]["postinstall"] = "ng build --aot --prod"

if args.heroku:
    move_from_dev_deps = ["@angular/compiler-cli", "@angular/cli",
                          "@angular-devkit/build-angular", "typescript"]
    for dep in move_from_dev_deps:
        angular_package_json["dependencies"][dep] = angular_package_json["devDependencies"][dep]
        del angular_package_json["devDependencies"][dep]

with open("package.json", "w") as write:
    write.write(json.dumps(angular_package_json, indent=4))

os.chdir(node_path)

os.system("git add .")
os.system("git commit -m \"Initial commit\"")
os.system("git branch -M main")
if args.git is not None:
    ssh_url = args.git.replace("https://", "git@").replace("/", ":", 1)+".git"
    os.system(f"git remote add origin {ssh_url}")
    os.system("git push -u origin main")
