import os
import re
import tempfile
from json import JSONEncoder

from colorclass.color import Color
from dexsim import get_value
from dexsim.plugin import Plugin

PLUGIN_CLASS_NAME = "Geost"

# fill-array-data v2, :array_2e
# invoke-virtual {p0, v2}, Lcom/rgamtgid/hnsolues/QLwdDnU;->UGanmSarY([B)[B
# move-result-object v2
# invoke-direct {v1, v2}, Ljava/lang/String;-><init>([B)V

# r'fill-array-data v\d+, :(\w+)\s+?'
# r'invoke-virtual {p\d, v\d}, (.*?);->(.*?)\(\[B\)\[B\s+?'
# r'move-result-object v\d+\s+?'
# r'invoke-direct {(v\d+), v\d+}, Ljava/lang/String;-><init>\(\[B\)V'


# fill-array-data     v3, :774
# move-object/from16  v0, p0
# invoke-virtual      {v0, v3}, Lcom/rgamtgid/hnsolues/QLwdDnU;->UGanmSarY([B)[B
# move-result-object  v3
# invoke-direct       {v2, v3}, Ljava/lang/String;-><init>([B)V

# r'fill-array-data v\d+, :(\w+)\s+?'
# r'move-object/from16 v\d+, p0\s+?'
# r'invoke-virtual {v\d, v\d}, (.*?);->(.*?)\(\[B\)\[B\s+?'
# r'move-result-object v\d+\s+?'
# r'invoke-direct {(v\d+), v\d+}, Ljava/lang/String;-><init>\(\[B\)V'

class Geost(Plugin):
    name = PLUGIN_CLASS_NAME
    enabled = True
    tname = None
    index = 3

    def __init__(self, driver, smalidir):
        Plugin.__init__(self, driver, smalidir)

    def run(self):
        if self.ONE_TIME:
            return
        self.ONE_TIME = True
        print("++++++++++++++++++++++++")
        print('Run ' + __name__, end=' ', flush=True)

        regex = (
            r'fill-array-data v\d+, :(\w+)\s+?'
            r'invoke-virtual {p\d, v\d}, (.*?);->(.*?)\(\[B\)\[B\s+?'
            r'move-result-object v\d+\s+?'
            r'invoke-direct {(v\d+), v\d+}, Ljava/lang/String;-><init>\(\[B\)V'
        )
        print("++++++++++++++++++++++++")
        ptn = re.compile(regex, re.MULTILINE)
        for sf in self.smalidir:
            for mtd in sf.get_methods():
                self._process_mtd(mtd, ptn)

        self.decode()

    def _process_mtd(self, mtd, ptn):
        # if get_value('DEBUG_MODE'):
        print('\n', '+' * 100)
        print('Starting to decode ...')
        print(Color.green(mtd))

        body = mtd.get_body()

        for item in ptn.finditer(body):
            old_content = item.group()  # 匹配到的内容，用来替换
            arg_pos, cname, mname, rtn_name = item.groups()
            cname = cname[1:].replace('/', '.')
            # 通过参数位置获取参数值
            rex = arg_pos + '\s*.array-data 1([\w\W\s]+?).end array-data'
            ptn_arr = re.compile(rex, re.MULTILINE)
            bjson = []
            for it in ptn_arr.finditer(body):
                arr = it.groups()
                for i in arr[0].split("\n"):
                    i = i.strip()
                    if i == "":
                        continue
                    bjson.append(int(i.replace('t', ''), 16))
            arguments = ['[B:' + str(bjson)]
            print(Color.green(cname) + " " + str(arguments))
            json_item = self.get_json_item(cname, mname, arguments)
            self.append_json_item(json_item, mtd, old_content, rtn_name)

    def decode(self):
        if not self.json_list or not self.target_contexts:
            return

        jsons = JSONEncoder().encode(self.json_list)

        outputs = {}
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tfile:
            tfile.write(jsons)
        outputs = self.driver.decode(tfile.name)
        os.unlink(tfile.name)

        if not outputs:
            return

        for key, value in outputs.items():
            if key not in self.target_contexts:
                print(key, value, "not in")
                continue
            for mtd, old_content, new_content in self.target_contexts[key]:
                old_body = mtd.get_body()
                new_content = new_content.format(value[0])
                body = old_body.replace(old_content, new_content)
                mtd.set_body(body)
                self.make_changes = True
                mtd.set_modified(True)
              

        self.smali_files_update()


