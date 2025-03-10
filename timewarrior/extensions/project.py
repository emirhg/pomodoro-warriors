#!/usr/bin/env python3.10

import datetime

import utils, copy
import sys
import re, json, subprocess

SINGLE_KEY_SIZE = 1
FIRST_ENTRY = 0


class TimeReport:
    tasks = dict()
    projects = dict()
    duration = datetime.timedelta()
    start = end = None

    def getJrnlLogs(self, taskid, from_date, to_date):
        jrnl_args = f"--short -from {from_date.strftime('%Y-%m-%dT%H:%M')} -to {to_date.strftime('%Y-%m-%dT%H:%M:%S')}"
        command = f'taskopen jrnl --args="{jrnl_args}" --active-tasks="" {taskid}'
        jrnl_logs = subprocess.run(
            command,
            shell=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return (
            jrnl_logs.stdout if jrnl_logs.stdout != "No actions applicable.\n" else None
        )

    def getProjectForTaskId(self, id):
        project = None

        if id not in self.tasks:
            tmp_tasks = json.loads(subprocess.check_output(["task", id, "export"]))
            if len(tmp_tasks) > 0:
                self.tasks[id] = tmp_tasks[FIRST_ENTRY]
                task = self.tasks[id]
                if "project" not in tmp_tasks[FIRST_ENTRY]:
                    task["project"] = "NONE"
                project = task["project"]
            else:
                project = "NOT FOUND"
                task = {"description": id, "project": "NOT FOUND", "status": "unknown"}
            if project not in self.projects:
                self.projects[project] = dict()
                self.projects[project]["duration"] = datetime.timedelta(0)
            if "members" not in self.projects[project]:
                self.projects[project]["members"] = dict()
            if id not in self.projects[project]["members"]:
                self.projects[project]["members"][id] = task
                self.projects[project]["members"][id]["duration"] = datetime.timedelta(
                    0
                )
        else:
            task = self.tasks[id]
        project = task["project"]
        return project

    def print_task_jrnl(self, taskid):
        task_data = self.tasks[taskid]
        jrnl_logs = self.getJrnlLogs(taskid, task_data["start"], task_data["end"])
        if jrnl_logs:
            print("\n".join(f"{' ' * 35}{line}" for line in jrnl_logs.splitlines()))

    def print_task_data(self, task):
        project = self.getProjectForTaskId(task)
        task_data = self.tasks[task]

        segments = len(task_data["description"]) // 65
        print(f"\t{task_data['start']}", end="")
        for i in range(segments):
            print(
                f"\t{task_data['description'][(65 * i) : (65 * (i + 1))]}", end="...\n"
            )
        if segments > 0:
            print(" " * 31, end="")

        print(
            f"\t{task_data['description'][65 * segments :].ljust(70)}{task_data['status'].upper().ljust(13)}{task_data['duration']}"
        )
        self.print_task_jrnl(task)

    def print_total_time(self):
        total_seconds = self.duration.total_seconds()
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        print(
            f"Total: {self.start} - {self.end} {str().ljust(70)}"
            + ("%02i:%02i:%02i" % (hours, minutes, seconds))
        )

    def print_report_separator(self):
        print("=" * 135)

    def print_project_separator(self):
        print("-" * 135)

    def print_project_report(self):
        for project, details in self.projects.items():
            pduration = details["duration"]
            print(f"{project}")
            for task, task_data in details["members"].items():
                if len(task_data["description"]) < 65:
                    print(
                        f"\t{task_data['description'][:65].ljust(70)}{task_data['status'].upper().ljust(13)}{task_data['duration']}"
                    )
                else:
                    segments = len(task_data["description"]) // 65
                    for i in range(segments):
                        print(
                            f"\t{task_data['description'][(65 * i) : (65 * (i + 1))]}..."
                        )
                    print(
                        f"\t{task_data['description'][65 * segments :].ljust(70)}{task_data['status'].upper().ljust(13)}{task_data['duration']}"
                    )
            print(f"{str(pduration).rjust(108)}")
            self.print_project_separator()
        self.print_report_separator()
        self.print_total_time()


# TODO: Finish nesteed values. How to handle when project has task and also subprojects? Two different keys must be used
def get_nested_value(dictionary, key, sep=".", default=None):
    keys = key.split(sep)
    first_level = dictionary.get(keys[FIRST_ENTRY], default)
    if len(keys) > SINGLE_KEY_SIZE:
        next_keys = sep.join(keys[SINGLE_KEY_SIZE:])
        return get_nested_value(first_level)
    else:
        return first_level


def main():
    _, entries = utils.format_inputs()
    now = datetime.datetime.now()
    task_project_map, task_duration = dict(), dict()
    time_report = TimeReport()
    duration = datetime.timedelta()
    start = end = None
    switchProject = False
    project = taskid = None

    for entry in entries:
        start = utils.parse_utc(entry["start"])
        end = utils.parse_utc(entry["end"]) if "end" in entry else now
        time_report.duration += end - start
        matches = [
            tag
            for tag in entry["tags"]
            if re.match(r"^[\d\w]{8}-([\d\w]{4}-){3}[\d\w]{12}$", tag)
        ]
        if matches:
            if matches[FIRST_ENTRY] != taskid:
                if project and taskid:
                    time_report.print_task_data(taskid)
                else:
                    time_report.start = start
                taskid = matches[FIRST_ENTRY]
                if project != time_report.getProjectForTaskId(taskid):
                    if project:
                        print(f"\t{end} {str(duration).rjust(106)}")
                        time_report.print_project_separator()
                        duration = datetime.timedelta()
                    project = time_report.getProjectForTaskId(taskid)
                    print("%s" % project)
                time_report.tasks[taskid]["start"] = start
        else:
            print(
                "Task UUID not found. Is the format right?\n\t%s" % str(entry),
                file=sys.stderr,
            )
            taskid = "NOT UUID"
        # task_project_map[taskid] = task_project_map.get(taskid, None) or time_report.getProjectForTaskId(taskid)

        duration += end - start
        time_report.tasks[taskid]["end"] = end
        time_report.projects[project]["duration"] += end - start
        time_report.projects[project]["members"][taskid]["duration"] += end - start
    time_report.end = end
    # Print last task
    if project and taskid:
        time_report.tasks[taskid]["end"] = end
        time_report.print_task_data(taskid)
        print(f"\t{end} {str(duration).rjust(106)}")
    taskid = matches[FIRST_ENTRY]

    time_report.print_report_separator()
    time_report.print_total_time()


# time_report.print_project_report()


main()
