"""
ROADMAP

To do:

Add shebang
!/usr/bin/env python3
chmod +x ./mm.py

Create an SSH update/download method
 - p mm.py ssh dev|staging|live ul|dl remote_file local_file

Export diff log format
 - short insert on one line
 - long insert statement on one line

Export
 - List dir after export using os.path.listdir()
 - highlight the generated file

Write template name
 1 - Git stash save -m str("mm:"+md5('mm')) - allow git checkout to remove the tpl name
 2 - Write the template path+name on the first line of /folder/*.mustache tpl in specified folder
     ...
 3 - To undo git checkout theme/remui/*
 4 - git stash pop

Create a function to trigger debug
 - use admin/cli/cfg.php --name=function --set=value

Create a function that check files integrity
 - Check files that are in files table and not on the drive
 - Check files that on the drive and not in the file table

Suggest .sql.tar.gz
 - When creating a databases and the import statement is specified
   find *.sql.tar.gz and allow choose 1, 2, 3, etc

Deployment script
 - Create DB
 - GRANT ALL PRIVILEGES ON {new database} . * TO '{user}'@'localhost';
 - Import SQL
 - Copy md_xxx
 - chmod + chown md_xxx
 - git checkout remote branch

Done:
 - Use vagrant/vagrant as DB creds if not entered

"""

import getpass
# import MySQLdb as db
import mysql.connector as mysql
import os
import sys
import tarfile
import shutil
from pathlib import Path


class mm(object):
    """Moodle Manager"""

    # Current working directory
    wd = os.getcwd()

    # Default database directory
    dDir = os.path.join(os.getcwd(), 'backup')

    # Default location of Moodle's data directory
    mDir = "/var/www"

    # passed parameter to the script
    param = ''

    # Add default database credentials so we don't have to
    # supply them everytime at the prompt
    default_db_username = 'vagrant'
    default_db_password = 'vagrant'

    # HTML tpl for the template path
    tpl_path_container = "\n<span style=\"background-color:#000!important; color:#FFF!important;\">{}</span>\n"

    # color code \x1b[38;2;R;G;Bm
    CRED = "\x1b[38;2;176;0;32m"
    CBLUE = "\x1b[38;2;36;123;160m"
    CLBLUE = "\x1b[38;2;208;244;234m"
    CGREEN = "\x1b[38;2;58;125;68m"
    CEND = "\x1b[0m"

    def __init__(self, args):

        # initialize the utilities class
        # contains various usefull method
        self.utils = utils()

        # convert the args into a dictionary
        self.param = self.utils.cargs(args)

        # if not arguments given, print help
        if len(args) == 1:
            self.print_help()
        elif len(args) > 1:
            if args[1] == "create":
                self.create(args)
            elif args[1] == "export":
                self.export(args)
            elif args[1] == "fix":
                self.fix(args)
            elif args[1] == "fixutf":
                self.fixutf(args)
            elif args[1] == "plugin":
                self.plugin(args)
            elif args[1] == "md":
                self.datadir()
            elif args[1] == "pc":
                self.purgeCache()
            elif args[1] == "ct":
                self.runCronTask()
            elif args[1] == "tpl":
                self.tpl(args)

    def print_help(self):
        print("\n")

        self.utils.print_msg("create database [import] [archive]", self.CBLUE)
        self.utils.print_msg("\tCreate an utf8mb4 database and import a SQL dump if import is specified")
        self.utils.print_msg("\tdatabase : Database name", self.CLBLUE)
        self.utils.print_msg("\timport   : Import SQL switch.", self.CLBLUE)
        self.utils.print_msg("\tarchive  : File to import (without .sql.tar.gz)", self.CLBLUE)
        self.utils.print_msg("                   Default backup/database/database.sql.tar.gz\n", self.CLBLUE)

        self.utils.print_msg("tpl [write|reset] [folder]", self.CBLUE)
        self.utils.print_msg("\tDesc : Write the template path into the mustache tpl")
        self.utils.print_msg("\t[write|reset] write or remove the tpl path in the tpl file", self.CLBLUE)
        self.utils.print_msg("\t[folder] only templates within the specified folder will be written\n", self.CLBLUE)

        self.utils.print_msg("export database [archive]", self.CBLUE)
        self.utils.print_msg("\tExport the content of a database into a SQL file and compress it")
        self.utils.print_msg("\tdatabase : Database name", self.CLBLUE)
        self.utils.print_msg("\tarchive  : Archive file name. Default is database name.\n", self.CLBLUE)

        self.utils.print_msg("md archive folder", self.CBLUE)
        self.utils.print_msg("\tCreate a Moodle Data dir")
        self.utils.print_msg("\tarchive : name of the data dir archive without the tar.gz", self.CLBLUE)
        self.utils.print_msg("\tfolder : new Moodle's data dir name in " + self.mDir + "\n", self.CLBLUE)

        self.utils.print_msg("fixutf [SQL file]", self.CBLUE)
        self.utils.print_msg("\tFind and replace the varchar(x) column with a varchar(190)")
        self.utils.print_msg("\tSQL File : The SQL file to F&R in /backup/database\n", self.CLBLUE)

        self.utils.print_msg("fix", self.CBLUE)
        self.utils.print_msg("\tFix Database collation, compress rows and clear MOODLE's cache\n")

        self.utils.print_msg("ct task [showsql] [showdebugging]", self.CBLUE)
        self.utils.print_msg("\tRun a Moodle cron task")
        self.utils.print_msg("\ttask : The path to the task to run or group task name", self.CLBLUE)
        self.utils.print_msg("\t       Task name:", self.CLBLUE)
        self.utils.print_msg("\t       p3 mm.py ct '\\report_iomadanalytics\\task\\SystemOverview'", self.CLBLUE)
        self.utils.print_msg("\t       Must input task in ''\n", self.CLBLUE)
        self.utils.print_msg("\t       Task group:", self.CLBLUE)
        self.utils.print_msg("\t       p3 mm.py ct completion     => Run course & activity completion task", self.CLBLUE)
        self.utils.print_msg("\t       p3 mm.py ct iomadanalytics => Run report_iomadanalytics tasks", self.CLBLUE)
        self.utils.print_msg("\t       p3 mm.py ct list           => List all available task", self.CLBLUE)
        self.utils.print_msg("\tshowsql : Trigger the --showsql option. Default doesn't show SQL.", self.CLBLUE)
        self.utils.print_msg("\tshowdebugging : Trigger the --showdebugging option. Default doesn't show debug.\n", self.CLBLUE)

        self.utils.print_msg("pc", self.CBLUE)
        self.utils.print_msg("\tPurge MOODLE's cache\n")

        self.utils.print_msg("plugin [force]", self.CBLUE)
        self.utils.print_msg("\tInstall missing plugin from Github and add them to .gitignore")
        self.utils.print_msg("\tforce : Delete plugin if it exists \n", self.CLBLUE)

    def tpl(self, args):
        """ Write the template path into the mustache tpl """
        """ tpl [write|reset] [folder] """

        # check if we are writing or removing the tpl path in the files
        action = self.param[2]
        if (action == "write"):
            self.writeTpl(args)
        else:
            self.resetTpl(args)

    def writeTpl(self, args):
        """ Write the path of the template in the specified folder """

        # get the folder to work with
        if 3 in self.param:
            param_folder = self.param[3]
        else:
            self.utils.print_error("*** [folder] must be specified ***")
            self.utils.print_msg("ie: mm.py tpl write theme/boost")
            exit()

        directory = os.path.join(self.wd, param_folder)

        for tplFile in os.listdir(directory):
            if tplFile.endswith(".mustache"):
                tplFullPath = os.path.join(directory, tplFile)
                with open(tplFullPath, 'r') as original: original_tpl = original.read()
                print(original_tpl)
                exit()
                # with open(tplFile, mode='a+', encoding='UTF-8') as file:
                #     self.utils.print_status("Writing: " + param_folder + file.name)
                #     with open('filename', 'w') as modified: modified.write("new first line\n" + data)
                #     # Append text at the end of file
                #     file.write(self.tpl_path_container.format(param_folder + file.name))
                #     file.close()
                continue
            else:
                continue


    def resetTpl(self, args):
        """ Reset/remove the template path from the template files """
        """ using git checkout """
        print(args)

    def create(self, args):
        """
        Create an UTF8 database as Moodle expects it
        p3 mm.py create dbname import archive
        """

        # database name param is mandatory
        if 2 not in self.param:
            self.utils.print_error("*** [database] must be specified ***")
            self.utils.print_msg("p3 mm.py create dbName")
            self.utils.print_msg("dbName: Name of the database to create")
            exit()

        dbName = self.param[2]

        # get a MySQL connection
        db = self.utils.getDbConn(dbName)
        cursor = db.cursor()

        self.utils.print_status("Setting innodb_default_row_format")
        cursor.execute("SET GLOBAL innodb_default_row_format = DYNAMIC;")

        self.utils.print_status("Setting collation_server")
        cursor.execute("SET GLOBAL collation_server = utf8mb4_unicode_ci;")

        self.utils.print_status("Setting collation_database")
        cursor.execute("SET GLOBAL collation_database = utf8mb4_unicode_ci;")

        self.utils.print_status("Setting collation_connection")
        cursor.execute("SET GLOBAL collation_connection = utf8mb4_unicode_ci;")

        self.utils.print_status("Setting innodb_file_format")
        cursor.execute("SET GLOBAL innodb_file_format=Barracuda;")

        self.utils.print_status("Setting innodb_file_per_table")
        cursor.execute("SET GLOBAL innodb_file_per_table=1;")

        self.utils.print_status("Setting innodb_large_prefix")
        cursor.execute("SET GLOBAL innodb_large_prefix=1;")

        self.utils.print_status("Dropping database {}.".format(dbName))
        cursor.execute("DROP DATABASE IF EXISTS " + dbName + ";")
        self.utils.print_status("Database {} dropped.".format(dbName))

        self.utils.print_status("Creating database {}.".format(dbName))
        cursor.execute("CREATE DATABASE " + dbName + " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        self.utils.print_status("Database {} created.".format(dbName))

        # database name param is mandatory
        if 3 not in self.param:
            self.utils.print_msg("Create database " + dbName + " completed.")
            exit()

        if 4 in self.param:

            # archive's file name of the MySQL dump file to import
            archive = self.param[4] + '.sql.tar.gz'

            # if the archive exists, extract the SQL file from the archive
            if os.path.isfile(os.path.join(self.dDir, archive)):
                self.utils.print_status("Starting import of {}".format(self.param[2]))
                self.utils.print_status("Deflate {}".format(archive))
                os.chdir(self.dDir)

                # open the archive
                tf = tarfile.open(archive)

                # Get the database dump file name in the archive
                # The archive must be the first file in the archive
                dumpFile = tf.getnames()[0]

                # Remove the ._ string that Mac add at the begining of the file name in the archive name
                if dumpFile.count('._'):
                    dumpFile = dumpFile[2:]

                tf.extractall()

                # import the extracted dump file into the database
                self.utils.print_status("Importing {} into {}".format(dumpFile, dbName))
                os.system("mysql -u{} -p{} {} < {}".format(self.utils.dbUserName, self.utils.dbPassword, dbName, os.path.join(self.dDir, dumpFile)))

                # remove the imported SQL dump file
                if os.path.isfile(dumpFile):
                    os.remove(dumpFile)
            else:
                self.utils.print_error("*** archive must exists ***")
                self.utils.print_msg("p3 mm.py create dbName import archive")
                self.utils.print_msg("archive: Name of the SQL dump file in " + self.dDir)
                self.utils.print_msg("archive must be specified without the .sql.tar.gz extension")
                exit()
        else:
            self.utils.print_error("*** archive must be specified ***")
            self.utils.print_msg("p3 mm.py create dbName import archive")
            self.utils.print_msg("archive: Name of the SQL dump file in " + self.dDir)
            self.utils.print_msg("archive must be specified without the .sql.tar.gz extension")
            exit()

    def export(self, args):
        """ ./mm.py export [database] [archive] """
        """ Export a SQL file from [database] using mysqldump """

        # define dababase name
        dbName = args[2]

        # define archive name, if not supplied use database name as archive name
        if len(args) < 4:
            archive = args[2]
        else:
            archive = args[3]

        archive += ".sql"

        # define dump file with full path
        dFile = os.path.join(self.dDir, archive)

        # get a MySQL connection
        db = self.utils.getDbConn(dbName)
        cursor = db.cursor()

        # output moodle database as backup
        self.utils.print_status("Starting: MySQL Dump")
        os.system("mysqldump --user=" + self.utils.dbUserName + " --password=" + self.utils.dbPassword + " " + dbName + " --opt --no-create-db > " + dFile)

        self.utils.print_status("Starting: Compress {}".format(archive))

        # Change working dir to /database dir
        os.chdir(self.dDir)

        # Compress MySQL dump
        dump = tarfile.open(archive + ".tar.gz", mode='w:gz')
        try:
            self.utils.print_msg("    Adding {}".format(archive))
            dump.add(archive)
        finally:
            self.utils.print_msg("    Closing {}".format(archive))
            dump.close()

        # Delete the .sql dump file
        if os.path.isfile(archive):
            os.remove(archive)

        self.utils.print_status("Task Completed")

        # list the database folder
        self.utils.print_status("Listing: " + self.dDir)
        os.system("ls -lh {}".format(self.dDir))

    def fix(self, args):
        """
        Fix Character encoding and row compression in a MySQL database
        """
        self.utils.print_status("Fixing collation")
        os.system("/usr/bin/php {} --collation=utf8mb4_unicode_ci".format(
            os.path.join(self.wd, "admin/cli/mysql_collation.php")
        ))

        self.utils.print_status("Compressing rows")
        os.system("/usr/bin/php {} --fix".format(
            os.path.join(self.wd, "admin/cli/mysql_compressed_rows.php")
        ))

        # purge Moodle's cache
        self.utils.print_status("Purging Moodle's Cache")
        self.purgeCache()

    def fixutf(self, args):
        """
        Fix varchar() column in the export.sql before importing it
        Set all varchar(>190) to varchar(190) to avoid key length error when importing in MySQL/MariaDB
        $1 refers to the file name argument passed to the function
        ./cdb.sh fixutf would set $db to default value: export.sql
        ./cdb.sh fixutf kpmy.sql would set $db to kpmy.sql
        """

        # use default file name if none is passed
        if 2 in self.param:
            db = self.param[2] + ".sql"
        else:
            db = "export.sql"

        # join the default database dir with the SQL dump file
        dFile = os.path.join(self.dDir, db)

        if os.path.isfile(dFile):
            self.utils.print_status("F+R varchar(1333)")
            os.system("sed -i 's/varchar(1333) COLLATE utf8mb4_unicode_ci/varchar(190) COLLATE utf8mb4_unicode_ci/g' " + dFile)
            self.utils.print_status("F+R varchar(255)")
            os.system("sed -i 's/varchar(255) COLLATE utf8mb4_unicode_ci/varchar(190) COLLATE utf8mb4_unicode_ci/g' " + dFile)
            self.utils.print_status("F+R varchar(200)")
            os.system("sed -i 's/varchar(200) COLLATE utf8mb4_unicode_ci/varchar(190) COLLATE utf8mb4_unicode_ci/g' " + dFile)
            self.utils.print_status("ROW_FORMAT=COMPRESSED")
            os.system("sed -i 's/ROW_FORMAT=COMPRESSED/ROW_FORMAT=DYNAMIC/g' " + dFile)
        else:
            self.utils.print_error("SQL file not found")

    def runCronTask(self):
        """
        Run a Moodle cron task
        p3 mm.py ct task | task_group
        p3 mm.py ct \\report_iomadanalytics\\task\\SystemOverview
        p3 mm.py ct completion
        """
        if 2 not in self.param:
            self.utils.print_error("task path or group name must be specified.")
            self.utils.print_msg("Read doc for task group name")
            exit()

        # Trigger the --showsql and --showdebugging switch. Off by default.
        showsql = False
        showdebugging = False
        for i in [3, 4]:
            if i in self.param:
                if self.param[i] == 'showsql':
                    showsql = True
                if self.param[i] == 'showdebugging':
                    showdebugging = True

        if self.param[2] == 'completion':
            taskToRun = [
                '\\core\\task\\completion_daily_task',
                '\\core\\task\\completion_regular_task'
            ]
        elif self.param[2] == 'iomadanalytics':
            taskToRun = [
                '\\report_iomadanalytics\\task\\GradesFilters',
                '\\report_iomadanalytics\\task\\SystemOverview'
            ]
        else:
            taskToRun = [self.param[2]]

        for task in taskToRun:
            self.utils.executeCronTask(task, showsql, showdebugging)

    def purgeCache(self):
        """
        Purge Moodle's cache
        """
        self.utils.purgeMoodleCache()

    def plugin(self, args):
        """
        Install all plugin from Github
        """

        # Force switch
        force = False
        if 2 in self.param:
            if self.param[2] == 'force':
                force = True

        # define the dictionary of plugin
        plugins = {
            'kpdesktop': {
                'url': "git@github.com:ndalpe/kpdesktop.git",
                'path': 'theme/kpdesktop',
                'branch': 'master'
            },
            'iomadfollowup': {
                'url': 'git@github.com:ndalpe/studentsfollowup.git',
                'path': 'report/iomadfollowup',
                'branch': 'master'
            },
            'iomadanalytics': {
                'url': 'git@github.com:ndalpe/iomadanalytics.git',
                'path': 'report/iomadanalytics',
                'branch': 'master'
            },
            'multilang2': {
                'url': 'git@github.com:iarenaza/moodle-filter_multilang2.git',
                'path': 'filter/multilang2',
                'branch': 'master'
            },
            'deferredallnothing': {
                'url': 'git@github.com:dthies/moodle-qbehaviour_deferredallnothing.git',
                'path': 'question/behaviour/deferredallnothing',
                'branch': 'master'
            },
            'filtered_course_list': {
                'url': 'git@github.com:CLAMP-IT/moodle-blocks_filtered_course_list.git',
                'path': 'blocks/filtered_course_list',
                'branch': 'master'
            }
        }

        for pluginName, pluginInfo in plugins.items():
            # Get the plugin abs path
            pluginPath = os.path.join(self.wd, pluginInfo['path'])

            # Test if the plugin is already installed
            if not os.path.isdir(pluginPath):
                self.utils.install_plugin(pluginName, pluginInfo)
            elif os.path.isdir(pluginPath) and force:
                shutil.rmtree(pluginPath)
                self.utils.install_plugin(pluginName, pluginInfo)
            else:
                self.utils.print_status("Skipping " + pluginName)

    def datadir(self):
        """
        Create a Moodle Data dir
        md archive folder
        """

        # archive param is mandatory
        if 2 not in self.param:
            self.utils.print_error("*** [archive] must be specified ***")
            self.utils.print_msg("p3 mm.py archive")
            self.utils.print_msg("archive: archive name without the .tar.gz extension")
            exit()

        # Make sure the archive file exists
        if not os.path.isfile(os.path.join(self.dDir, self.param[2] + ".tar.gz")):
            self.utils.print_error("*** [archive] must exists ***")
            self.utils.print_msg("p3 mm.py archive")
            self.utils.print_msg("archive: archive name without the .tar.gz extension")
            exit()

        # Make sure the archive is a tar file
        if not tarfile.is_tarfile(os.path.join(self.dDir, self.param[2] + ".tar.gz")):
            self.utils.print_error("*** [archive] must be a .tar.gz file format ***")
            self.utils.print_msg("p3 mm.py archive")
            self.utils.print_msg("archive: archive name without the .tar.gz extension")
            exit()

        # folder param is mandatory
        if 3 not in self.param:
            self.utils.print_error("*** [folder] must be specified ***")
            self.utils.print_msg("p3 mm.py archive folder")
            self.utils.print_msg("folder: name of Moodle's data directory")
            exit()

        # archive name
        archiveName = self.param[2] + ".tar.gz"

        # Archive containing the Moodle data dir
        archive = os.path.join(self.dDir, archiveName)

        # New Moodle data directory to create
        if 3 in self.param:
            newDD = os.path.join(self.mDir, self.param[3])
            if os.path.isdir(newDD):
                overwrite = input("Overwrite " + newDD + " ? (y/n)")
                if overwrite == 'y':
                    # delete the existing dir
                    self.utils.print_status("Deleting current " + newDD)
                    # shutil.rmtree(newDD)
                    os.system("sudo rm -R " + newDD)
                else:
                    self.utils.print_error("Declined overwrite of " + newDD)
                    exit()

        # check the dir name in archive
        tar = tarfile.open(archive)

        # get the path of the first file in the archive
        archivePath = Path(tar.getnames()[1])

        # get the root Moodle data dir in archive
        dirInArchive = archivePath.parts[0]

        # close the archive for now
        tar.close()

        # test if the dir in archive already exists in mDir
        tmpMDir = os.path.join(self.mDir, dirInArchive)

        if os.path.isdir(tmpMDir):
            overwrite = input("Overwrite " + tmpMDir + " ? (y/n)")
            if overwrite == 'y':
                # delete the existing dir
                self.utils.print_status("Deleting current " + tmpMDir)
                os.system("sudo rm -R " + tmpMDir)
            else:
                self.utils.print_error("Declined overwrite of " + tmpMDir)
                exit()

        # copy the archive in mDir
        self.utils.print_status("Copy " + archive)
        os.system("sudo cp -rp {} {}".format(archive, self.mDir))

        # extract the archive
        self.utils.print_status("Extracting " + archive + " in " + self.mDir)
        os.system("sudo tar --extract --file={} --directory={}".format(archive, self.mDir))

        # rename the extracted dir if [folder] param is different
        if 3 in self.param:
            if dirInArchive != self.param[3]:
                self.utils.print_status("Renaming {} to {}".format(dirInArchive, self.param[3]))
                os.rename(
                    os.path.join(self.mDir, dirInArchive),
                    os.path.join(self.mDir, self.param[3]),
                )

        # remove the archive from mDir
        self.utils.print_status("Removing " + os.path.join(self.mDir, archiveName))
        os.system("sudo rm " + os.path.join(self.mDir, archiveName))

        self.utils.print_status("Completed")

        os.system("ls -lsh " + self.mDir)


class utils(mm):
    def __init__(self):
        pass

    def print_error(self, msg):
        """
        Print red error message
        """
        print(self.CRED + msg + self.CEND)

    def print_status(self, msg):
        """
        Print red error message
        """
        print("\n" + self.CGREEN + "Status ==> " + self.CEND + msg)

    def print_msg(self, msg, color=False):
        """
        Print a colored message
        """
        if len(msg) > 0:
            if not color:
                print(msg)
            else:
                print(color + msg + self.CEND)

    def purgeMoodleCache(self):
        """
        Shortcut to clear Moodle's cache
        """
        self.print_status("Clearing Moodle's cache")
        os.system("/usr/bin/php {}".format(
            os.path.join(self.wd, "admin/cli/purge_caches.php")
        ))

    def executeCronTask(self, task, showsql=False, showdebugging=False):
        """
        Execute a single cron task or list all available tasks
        """

        # Make sure we have a task
        if len(task) == 0:
            self.print_error("task path must be specified")
            exit()

        cron_script = os.path.join(os.getcwd(), "admin/tool/task/cli/schedule_task.php")

        # List all available tasks in Moodle's cron task database
        # or execute a specific task
        if task == 'list':
            os.system("/usr/bin/php " + cron_script + " --list")
        elif task == 'all':
            os.system("/usr/bin/php admin/cli/cron.php")
        else:
            # Trigger the showsql switch
            if showsql is True:
                showSqlSwitch = ' --showsql'
            else:
                showSqlSwitch = ''

            # Trigger the showdebugging switch
            if showdebugging is True:
                showDebuggingSwitch = ' --showdebugging'
            else:
                showDebuggingSwitch = ''

            self.print_status(task)
            os.system("/usr/bin/php " + cron_script + showSqlSwitch + showDebuggingSwitch + " --execute='" + task + "'")

    def getDbConn(self, dbName=""):
        """
        Get a database connect and return cursor
        """

        # if username is not suplied, use the default database username
        self.dbUserName = input("Please enter MySQL username ({}): ".format(self.default_db_username))
        if self.dbUserName == "":
            self.dbUserName = self.default_db_username

        # if password is not suplied, use the default database password
        self.dbPassword = getpass.getpass('Please enter MySQL password ({}):'.format(self.default_db_password))
        if self.dbPassword == "":
            self.dbPassword = self.default_db_password

        if dbName != "":
            MySQLConn = mysql.connect(user=self.dbUserName, passwd=self.dbPassword)
        else:
            MySQLConn = mysql.connect(user=self.dbUserName, passwd=self.dbPassword, db=dbName)

        return MySQLConn

    def cargs(self, args):
        """
        Convert the args list into a dictionary
        """
        dictArgs = {i: args[i] for i in range(0, len(args))}
        return dictArgs

    def install_plugin(self, pluginName, pluginInfo):
        """
        Install plugin
        """
        self.print_status("Installing " + pluginName)

        os.system("git clone {} {}".format(pluginInfo['url'], pluginInfo['path']))

        if pluginInfo['branch'] != 'master':
            self.print_status("Tracking {}".format(pluginInfo['branch']))

            os.chdir(os.path.join(self.wd, pluginInfo['path']))
            os.system("git branch --track {} origin/{}".format(pluginInfo['branch'], pluginInfo['branch']))

            self.print_status("Checking out " + pluginInfo['branch'])
            os.system("git checkout {}".format(pluginInfo['branch']))

            # set the cwd to the project's root
            os.chdir(self.wd)

        self.print_status("Ignoring {}\n\n".format(pluginName))
        os.system("echo {} >> .git/info/exclude".format(pluginInfo['path']))


a = mm(sys.argv)
