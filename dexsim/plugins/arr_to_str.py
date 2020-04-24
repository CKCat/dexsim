import os
import re
import tempfile
from json import JSONEncoder

from colorclass.color import Color
from dexsim import get_value
from dexsim.plugin import Plugin

PLUGIN_CLASS_NAME = "arr_to_str"

# new-instance v3, Ljava/lang/String;
# sget-object v4, Lxdsn/mfdl/msla/b/b;->Q:[B
# invoke-direct {v3, v4}, Ljava/lang/String;-><init>([B)V


class arr_to_str(Plugin):
    name = PLUGIN_CLASS_NAME
    enabled = False
    tname = None
    index = 3

    def __init__(self, driver, smalidir):
        Plugin.__init__(self, driver, smalidir)

    def run(self):
        if self.ONE_TIME:
            return
        self.ONE_TIME = True
        print('Run ' + __name__, end=' ', flush=True)

        regex =(
            r'new-instance (v\d+), Ljava/lang/String;\s+?'
            r'sget-object v\d+, (.*?;->.*?):\[B\s+?'
            r'invoke-direct {v\d+, v\d+}, Ljava/lang/String;-><init>\(\[B\)V'
        )

        ptn = re.compile(regex, re.MULTILINE)
        for sf in self.smalidir:
            for mtd in sf.get_methods():
                self._process_mtd(mtd, ptn)

        self.decode()

    def _process_mtd(self, mtd, ptn):

        body = mtd.get_body()

        for item in ptn.finditer(body):
            old_content = item.group()  # 匹配到的内容，用来替换
            rtn_name, fname= item.groups()
            print(rtn_name, fname)

            json_item = self.get_json_item("", "", fname)
            self.append_json_item(json_item, mtd, old_content, rtn_name)

    def decode(self):
        if not self.json_list or not self.target_contexts:
            return

        
        regex =(
            r'new-array v0, v\d, \[B\s+?'
            r'fill-array-data v0, :(\w+)\s+?'
            r'sput-object v0, (.*?;->.*?):\[B'
        )
        ptn = re.compile(regex, re.MULTILINE)

        outputs = {}
        for sf in self.smalidir:
            for mtd in sf.get_methods():
                body = mtd.get_body()
                for item in ptn.finditer(body):
                    arg_pos, fname= item.groups()
                    rex = arg_pos + '\s*\.array-data 1([\w\W\s]+?)\.end array-data'
                    ptn_arr = re.compile(rex, re.MULTILINE)
                    bjson = []
                    for it in ptn_arr.finditer(body):
                        arr = it.groups()
                        data = arr[0].split("\n")
                        for i in data:
                            i = i.strip()
                            if i == "":
                                continue
                            bjson.append(chr(int(i.replace('t', ''), 16)))
                    ret = "".join(bjson) # 解密结果
                    ret = ret.replace(r'"', r'\"')
                    json_item = self.get_json_item("", "", fname)
                    mid = json_item["id"]
                    outputs[mid] = [ret]
    

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
