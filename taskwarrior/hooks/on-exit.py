#!/usr/bin/env python3.10

import os
import subprocess

import utils


RESERVED_TAGS = set("nocolor nonag nocal next".split())


def main():
    inputs = utils.format_inputs()
    args, cmd = inputs["args"], inputs["command"]
    if cmd == "split":
        # task <id> split <mods>
        pre, mods = args.split(cmd, 1)
        print(pre, mods, sep="\n")
        _id = int(pre.split()[1])
        mods = (
            (mods + " ")
            .replace(" project: ", "")
            .replace(" project:", " project:{}.")
            .strip()
        )
        if " project:" not in mods:
            mods += " project:{}"
        subid = subprocess.getoutput(
            "task _get %s.project | "
            "xargs -I{} task add %s | "
            'grep -o "[0-9]\\+"' % (_id, mods)
        )
        if subid:
            print("Created task %s." % (subid))
            os.system("task %s modify depends:%s" % (_id, subid))
        else:
            print("You can only split a task when it is a project.")
    elif cmd == "timew":
        # task <id> timew ...
        pre, timew = args.split(cmd, 1)
        _id = int(pre.split()[1])
        proj = subprocess.getoutput("task _get %s.project" % (_id))
        tags, uuid = subprocess.getoutput(
            "task _get %s.tags %s.uuid" % (_id, _id)
        ).split(" ", 2)
        tags = [t for t in tags.split(",") if t and t not in RESERVED_TAGS]
        while proj:
            tags.append(proj)
            proj = proj.rpartition(".")[0]
        tags.append(uuid)
        tags = " ".join('"%s"' % t for t in tags)
        subprocess.run("timew %s %s && task %s start" % (timew, tags, _id), shell=True)


main()
