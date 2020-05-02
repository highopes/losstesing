#!/usr/bin/env python
###################################################################################
#                           Written by Wei, Hang                                  #
#                          weihang_hank@gmail.com                                 #
###################################################################################
"""
This application helps to detect transient outages on lines that are often difficult
to detect by other detection tools, and the ACI provides atomic counter as a telemetry
method that can locate and graphically display it.
"""
import cobra.mit.access
import cobra.mit.access as mo
import cobra.mit.session as session
import cobra.mit.request
import cobra.mit.session
import datetime
import time
import MySQLdb
from Tkinter import *
import ttk
import requests
from tkMessageBox import *

requests.packages.urllib3.disable_warnings()
class telemetry:

    def __init__(self):
        self.root = Tk()
        self.root.title('闪断检测程序')
        self.root.geometry("1150x800")
        self.root.resizable(width=True, height=False)
        self.client_input()
        self.top_canvas = Canvas(self.root, width=1100, height=350, bg='yellow')
        self.top_canvas.pack()
        self.list_box = Canvas(self.root)
        self.vbar = ttk.Scrollbar(self.list_box, orient=VERTICAL)
        self.start_time = StringVar
        # init
        self.aci_adress = 'http://10.124.4.101'

        self.mo = cobra.mit.access
        self.spine_img = PhotoImage(file='images/spine.gif')
        self.leaf_img = PhotoImage(file='images/leaf.gif')
        self.heading_columns = ['Time', 'name', 'Drop', 'DropPrecent', 'Totdrop', 'Tottras', 'Totrecv']
        self.heading_text = ['更新时间', '路径', '当前丢包数', '当前丢包率', '总丢包数', '总发包数', '总收包数']
        self.heading_width = [190, 300, 70, 70, 70, 200, 200]
        if len(self.heading_width) != len(self.heading_columns):
            raise ValueError

        self.db = MySQLdb.connect('127.0.0.1', 'root', 'Will9455', 'Cisco_Aci')
        self.cursor = self.db.cursor()
        self.tree = ttk.Treeview()

        self.root.mainloop()



    # client input
    def client_input(self):
        top_bar = Frame(self.root)
        Label(top_bar, text='叶子节点1：').pack(side=LEFT)
        leaf_1 = Entry(top_bar)
        leaf_1.pack(side=LEFT)

        Label(top_bar, text='叶子节点2：').pack(side=LEFT)
        leaf_2 = Entry(top_bar)
        leaf_2.pack(side=LEFT)

        btn_search = Button(top_bar, text='查询', command=lambda: self.execution(self.root, leaf_1.get(), leaf_2.get()))
        btn_search.pack(side=LEFT)
        top_bar.pack()

    """execute when input"""
    def execution(self, root, leaf_1, leaf_2):
        # refresh
        self.top_canvas.delete('all')
        self.tree.delete()
        self.list_box.destroy()
        [self.dbgAclist_spine, self.dbgAclist_leaf, self.dbgAclist_trail] = self.connect(leaf_1, leaf_2)

        if (leaf_2 != '' and leaf_1 != ''):
            self.canvas(root, self.dbgAclist_spine, self.dbgAclist_leaf, self.dbgAclist_trail)
        self.formlist(root, leaf_1, leaf_2)


    # connect to remote for service
    def connect(self, leaf_1, leaf_2):
        flag = 0
        self.mo_dir = self.mo.MoDirectory(session.LoginSession(self.aci_adress, 'admin', 'Cisco123'))
        self.start_time = time.time()
        self.mo_dir.login()

        self.clAcPath = cobra.mit.access.ClassQuery('fabricTrail')
        self.dbgAcPathA_objlist = self.mo_dir.query(self.clAcPath)
        self.dbgAclist_spine = []
        self.dbgAclist_leaf = []
        self.dbgAclist_trail = []

        for m in self.dbgAcPathA_objlist:
            # 根据用户选定特定的leaf的值
            if leaf_1 in str(m.rn) and leaf_2 in str(m.rn):
                self.dbgAclist_leaf.append(str(m.n1))
                self.dbgAclist_spine.append(str(m.transit))
                self.dbgAclist_trail.append(str(m.rn))
            else:
                flag += 1
        """当flag和长度相等时,说明没有找到对应路径"""
        if flag != len(self.dbgAcPathA_objlist):
            self.dbgAclist_spine = list(set(self.dbgAclist_spine))
            """数组中重复的去除,如201-102只能画一次"""
            self.dbgAclist_leaf = list(set(self.dbgAclist_leaf))
            return self.dbgAclist_spine, self.dbgAclist_leaf, self.dbgAclist_trail
        else:
            showerror("Answer", "Sorry, there is no trail bwtween the two leafs!")



    # 调用方法获取表格内容插入
    def get_tree(self, leaf_1, leaf_2):
        # update path
        clAcPath = cobra.mit.access.ClassQuery('dbgAcTrail')
        dbgAcPathA_objlist = self.mo_dir.query(clAcPath)
        # refresh timeout
        if(time.time() > self.start_time + 500):
            self.mo_dir = self.mo.MoDirectory(session.LoginSession(self.aci_adress, 'admin', 'Cisco123'))
            self.mo_dir.login()
            self.start_time = time.time()

        self.insertDB(dbgAcPathA_objlist)
        # objlist[0]代表第几条path
        now = datetime.datetime.now()
        if leaf_1 in str(dbgAcPathA_objlist[0].dn) \
                and leaf_2 in str(dbgAcPathA_objlist[0].dn):
            self.tree.insert("", END,
                             values=(now.strftime('%Y-%m-%d %H:%M:%S'),
                                     dbgAcPathA_objlist[0].dn,
                                     dbgAcPathA_objlist[0].dropPkt,
                                     dbgAcPathA_objlist[0].dropPktPercentage,
                                     dbgAcPathA_objlist[0].totDropPkt,
                                     dbgAcPathA_objlist[0].totRxPkt,
                                     dbgAcPathA_objlist[0].totTxPkt))
            self.tree.yview_moveto(1)
        # insert  1 record/2000ms
        self.tree.after(2000, lambda: self.get_tree(leaf_1, leaf_2))


    # 画出表单
    def formlist(self, root, leaf_1, leaf_2):
        self.list_box = Canvas(self.root)
        self.vbar = ttk.Scrollbar(self.list_box, orient=VERTICAL)
        self.vbar.pack(side=LEFT, fill=Y)
        # draw list and give name
        self.tree = ttk.Treeview(self.list_box,
                                 height=20,
                                 columns=self.heading_columns,
                                 show='headings',
                                 yscrollcommand=self.vbar.set)

        for i in range(len(self.heading_columns)):
                self.tree.heading(self.heading_columns[i],
                                  text=self.heading_text[i])
                self.tree.column(self.heading_columns[i],
                                 width=self.heading_width[i],
                                 anchor='center')

        self.get_tree(leaf_1, leaf_2)
        self.tree.pack()
        self.list_box.pack()


  # 画出特定链接
    def draw_line(self, canvas, trail):
        for item in trail:
            spine_item = canvas.find_withtag(item[6:9] + 'a')
            leaf1_item = canvas.find_withtag(item[10:13] + 'a')
            leaf2_item = canvas.find_withtag(item[14:17] + 'a')
            canvas.create_line(canvas.coords(spine_item)[0],
                               canvas.coords(spine_item)[1],
                               canvas.coords(leaf1_item)[0],
                               canvas.coords(leaf1_item)[1],
                               fill='red')

            canvas.create_line(canvas.coords(spine_item)[0],
                               canvas.coords(spine_item)[1],
                               canvas.coords(leaf2_item)[0],
                               canvas.coords(leaf2_item)[1],
                               fill='red')

 #构建画布，画出拓扑图
    def canvas(self, root,  spine_list, leaf_list, trail_list):
        for i in range(1, len(spine_list) + 1):
            self.top_canvas.create_image(600/len(spine_list)+(i-1)*1200/len(spine_list),
                                         50,
                                         image=self.spine_img,
                                         tags=spine_list[i - 2] + 'a')
            self.top_canvas.create_text(600/len(spine_list)+(i-1)*1200/len(spine_list),
                                        50 + 30,
                                        text=spine_list[i - 2],
                                        font=('微软雅黑', 20))

        for j in range(1, len(leaf_list) + 1):
            self.top_canvas.create_image(600/len(leaf_list)+(j-1)*1200/len(leaf_list),
                                         200,
                                         image=self.leaf_img,
                                         tags=leaf_list[j - 2] + 'a')
            self.top_canvas.create_text(600/len(leaf_list)+(j-1)*1200/len(leaf_list),
                                        200 + 60,
                                        text=leaf_list[j - 2],
                                        font=('微软雅黑', 20))

        self.draw_line(self.top_canvas, trail_list)
        self.top_canvas.pack()

    def insertDB(self, dbgAcPathA_objlist):
        # while TRUE:
        for i in dbgAcPathA_objlist:
            sql = "INSERT INTO acTrail(dn," \
                  " dropPkt," \
                  " trnstNodeId," \
                  " dropPktPercentage," \
                  " dstNodeId," \
                  " excessPkt," \
                  " excessPktPercentage," \
                  " pathType," \
                  " rxPkt," \
                  " srcNodeId," \
                  " suspect," \
                  " totDropPkt," \
                  " totDropPktPercentage," \
                  " totExcessPkt," \
                  " totExcessPktPercentage," \
                  " totRxPkt," \
                  " totTxPkt," \
                  " txPkt," \
                  " rn ) VALUES('%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s'," \
                  " '%s') " % (i.dn,
                               i.dropPkt,
                               i.trnstNodeId,
                               i.dropPktPercentage,
                               i.dstNodeId,
                               i.excessPkt,
                               i.excessPktPercentage,
                               i.pathType,
                               i.rxPkt,
                               i.srcNodeId,
                               i.suspect,
                               i.totDropPkt,
                               i.totDropPktPercentage,
                               i.totExcessPkt,
                               i.totExcessPktPercentage,
                               i.totRxPkt,
                               i.totTxPkt,
                               i.txPkt,
                               i.rn)
        self.cursor.execute(sql)
        self.db.commit()

if __name__ == '__main__':
    telemetry()