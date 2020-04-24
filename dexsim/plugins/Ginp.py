import os
import re
import tempfile
from json import JSONEncoder

from colorclass.color import Color
from dexsim import get_value
from dexsim.plugin import Plugin

PLUGIN_CLASS_NAME = "Ginp"

# const/16 v0, 0x24
# :try_start_2
# new-array v0, v0, [B
# fill-array-data v0, :array_56
# invoke-static {v0}, Li8/ma/d7/c;->O([B)Ljava/lang/String;
# move-result-object v0


class Ginp(Plugin):
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

        regex = (
            r'const-string [vp]\d+, "([a-zA-Z0-9=]+)"[\s\S]+?'
            r'invoke-virtual {p0, [vp]\d+}, L(.*?);->(.*?)\(Ljava/lang/String;\)Ljava/lang/String;[\s\S]+?'
            r'move-result-object ([vp]\d+)'
        )

        ptn = re.compile(regex, re.MULTILINE)
        for sf in self.smalidir:
            for mtd in sf.get_methods():
                self._process_mtd(mtd, ptn)

        self.decode()

    def _process_mtd(self, mtd, ptn):
        if get_value('DEBUG_MODE'):
            print('\n', '+' * 100)
            print('Starting to decode ...')
            print(Color.green(mtd))

        body = mtd.get_body()

        for item in ptn.finditer(body):
            old_content = item.group()  # 匹配到的内容，用来替换
            arg, cname, mname, rtn_name = item.groups()
            cname = cname.replace('/', '.')
            # 通过参数位置获取参数值
            print("class, method, ret, arg:", cname, mname, rtn_name, arg)
            arguments = ['java.lang.String:' + arg]
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
                new_content = old_content + "\n" + new_content.format(value[0])
                body = old_body.replace(old_content, new_content)
                mtd.set_body(body)
                self.make_changes = True
                mtd.set_modified(True)
              

        self.smali_files_update()
