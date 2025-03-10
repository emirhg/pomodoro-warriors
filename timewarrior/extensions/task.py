#!/usr/bin/env python3.10

import shutil
import datetime

import utils, copy
import sys, os
import re, json, subprocess

SINGLE_KEY_SIZE = 1
FIRST_ENTRY = 0
SEGMENT_SIZE = 65
ENABLE_LOGS = False


class JrnlReport:
    @staticmethod
    def get_logs(taskid, from_date, to_date):
        jrnl_args = f"--export json -from {from_date.strftime('%Y-%m-%dT%H:%M')} -to {to_date.strftime('%Y-%m-%dT%H:%M:%S')}"
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


class TimeReport:
    tasks = dict()
    projects = dict()
    duration = datetime.timedelta()
    start = end = None

    @staticmethod
    def getJrnlLogs(taskid, from_date, to_date):
        jrnl_args = f"--export json -from {from_date.strftime('%Y-%m-%dT%H:%M')} -to {to_date.strftime('%Y-%m-%dT%H:%M:%S')}"
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


class ReportProcessor:
    tasks = dict()
    config = dict()
    timew_entries = []

    strfdate = "W%U %Y-%m-%d %a"
    strftime = "%H:%M:%S"

    def __init__(self):
        self.config, self.timew_entries = utils.format_inputs()
        self.load_task_data()

    def cols_to_line(
        self, date=None, activity=None, duration=None, period_duration=None
    ):
        return "{:<19s}{:<100s}{:<9s}{}".format(
            date or "", activity or "", duration or "", period_duration or ""
        )

    def __str__(self):
        """Output the current report as a string"""
        report = ""
        last_entry = None
        last_project = None
        task_duration = datetime.timedelta()
        project_duration = datetime.timedelta()
        day_duration = datetime.timedelta()
        week_duration = datetime.timedelta()
        month_duration = datetime.timedelta()
        total_duration = datetime.timedelta()
        last_date = None

        for entry in self.timew_entries:
            project = self.tasks[entry.uuid].get("project", "")
            if last_project != project or last_date != entry.start.strftime(
                self.strfdate
            ):
                if (report_date := entry.start.strftime(self.strfdate)) == last_date:
                    report_date = ""
                else:
                    last_date = entry.start.strftime(self.strfdate)
                # Append project line
                report += (
                    self.cols_to_line(report_date, "{:<0s}{}".format("", project))
                    + "\n"
                )
                last_project = project

            if not last_entry or not last_entry.on_same_day(entry):
                cur_date = entry.start
                task_duration += entry.end - entry.start
            else:
                task_duration = entry.end - entry.start

            total_duration += entry.end - entry.start
            if (report_date := entry.start.strftime(self.strfdate)) == last_date:
                report_date = "{:>14s}".format(entry.start.strftime("%H:%M"))
            # Append Task line
            report += (
                self.cols_to_line(
                    report_date,
                    "{:<2s}{}\t{}".format("", entry.status, entry),
                    str(task_duration),
                )
                + "\n"
            )

            if ENABLE_LOGS and (
                jrnl_logs := JrnlReport.get_logs(entry.uuid, entry.start, entry.end)
            ):
                for line in jrnl_logs.splitlines():
                    # Append jrnl line
                    report += (
                        self.cols_to_line(None, "{:<4s}{}".format("", line)) + "\n"
                    )

            last_entry = entry

        report += self.cols_to_line(period_duration="      ") + "\n"
        report += self.cols_to_line(period_duration=str(total_duration)) + "\n"
        return report

    def load_task_data(self):
        uuids = []
        for idx, entry in enumerate(self.timew_entries):
            self.timew_entries[idx] = TimewEntry(entry)
            if self.timew_entries[idx].uuid:
                uuids.append(self.timew_entries[idx].uuid)

        command = "task {} export".format(" ".join(self.tasks.keys()))
        output = subprocess.run(
            command,
            encoding="UTF-8",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        tasks = json.loads(output.stdout)

        for task in tasks:
            self.tasks[task["uuid"]] = task

        for idx, entry in enumerate(self.timew_entries):
            try:
                self.timew_entries[idx].description = self.tasks[entry.uuid][
                    "description"
                ]
                self.timew_entries[idx].status = self.tasks[entry.uuid][
                    "status"
                ].upper()
            except Exception as exception:
                pass


class TimewEntry:
    uuid = None
    _desc = None

    def __init__(self, entry):
        self.start = utils.parse_utc(entry["start"])
        self.end = (
            utils.parse_utc(entry["end"]) if "end" in entry else datetime.datetime.now()
        )
        self.duration = self.end - self.start
        self.tags = entry["tags"]
        matches = [
            tag
            for tag in entry["tags"]
            if re.match(r"^[\d\w]{8}-([\d\w]{4}-){3}[\d\w]{12}$", tag)
        ]
        if matches:
            self.uuid = matches[FIRST_ENTRY]

    def on_same_day(self, entry: "TimewEntry"):
        return self.start.toordinal() == entry.start.toordinal()

    def same_task(self, entry: "TimewEntry"):
        return self.description == entry.description

    @property
    def description(self):
        return self._desc or ", ".join(self.tags)

    @description.setter
    def description(self, value):
        self._desc = value

    def __format__(self, format_spec):
        return str(self).__format__(format_spec)

    def __str__(self):
        try:
            terminal_width = os.get_terminal_size().columns
        except:
            terminal_width = 150

        # Calculate the available space for the UUID field
        # Adjust these values if needed
        other_fields_width = 53  # Approximate width for other fields
        desc_field_width = terminal_width - other_fields_width

        return f"%s" % (self.description)


def main():
    report = ReportProcessor()

    print(report)


main()
