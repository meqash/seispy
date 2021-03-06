#!/usr/bin/env python
'''
This is a script to select receiver functions in GUI.
Usage:      python pickrf_R.py -Sstation_name para.cfg
Functions:  Click waveform to select good/bad RFs.
            Click "plotRF" to plot good RFs in a .ps file.
            Click "finish" to delete bad RFs and close the window.
'''

import matplotlib.pyplot as plt
import os, sys, glob, re, shutil
import obspy
import numpy as np
import getopt
from matplotlib.widgets import Button
from operator import itemgetter
import initopts
import plotrf
try:
    import configparser
    config = configparser.ConfigParser()
except:
    import ConfigParser
    config = ConfigParser.ConfigParser()

def Usage():
    print("Usage:  python pickrf_R.py -Sstation_name para.cfg")

def get_sac():
    if  sys.argv[1:] == []:
        Usage()
        sys.exit(1)
    for o in sys.argv[1:]:
        if os.path.isfile(o):
            head = o
            break
    try:
        opts, args = getopt.getopt(sys.argv[1:], "S:h")
    except:
        print("invalid argument")
        sys.exit(1)
    for op, value in opts:
        if op == "-S":
            staname = value
        elif op == "-h":
            Usage()
            sys.exit(1)
        else:
            print("invalid argument")
            sys.exit(1)
    config.read(head)
    image_path = config.get('path', 'image_path')
    path = config.get('path', 'RF_path')
    cut_path = config.get('path', 'out_path')
    path = os.path.join(path, staname)
    cut_path = os.path.join(cut_path, staname)
    files = glob.glob(os.path.join(path, '*_R.sac'))
    filenames = [re.match('\d{4}\D\d{3}\D\d{2}\D\d{2}\D\d{2}', os.path.basename(fl)).group() for fl in files]
    filenames.sort()
    rffiles = obspy.read(os.path.join(path, '*_R.sac'))
    return rffiles.sort(['starttime']), filenames, path, image_path, cut_path, staname

def indexpags(maxidx, evt_num):
    axpages = int(np.floor(evt_num/maxidx)+1)
    print('A total of '+str(evt_num)+' PRFs')
    rfidx = []
    for i in range(axpages-1):
        rfidx.append(range(maxidx*i, maxidx*(i+1)))
    rfidx.append(range(maxidx*(axpages-1), evt_num))
    return axpages, rfidx

class plotrffig():

    fig = plt.figure(figsize=(12, 11), dpi=60)
    axnext = plt.axes([0.81, 0.91, 0.07, 0.03])
    axprevious = plt.axes([0.71, 0.91, 0.07, 0.03])
    axfinish = plt.axes([0.91, 0.91, 0.07, 0.03])
    axPlot = plt.axes([0.1, 0.91, 0.07, 0.03])
    ax = plt.axes([0.16, 0.05, 0.5, 0.84])
    ax_baz = plt.axes([0.72, 0.05, 0.23, 0.84])
    ax.grid()
    ax_baz.grid()
    ax.set_ylabel("Event", fontsize=20)
    ax.set_xlabel("Time after P (s)")
    ax.set_title("R component")
    ax_baz.set_xlabel("Backazimuth (\N{DEGREE SIGN})")
    bnext = Button(axnext, 'Next')
    bprevious = Button(axprevious, 'Previous')
    bfinish = Button(axfinish, 'Finish')
    bplot = Button(axPlot, 'Plot RFs')

    def __init__(self, opts):
        self.opts = opts
        ax = self.ax
        ax_baz = self.ax_baz
        axpages, rfidx = indexpags(opts.maxidx, opts.evt_num)
        self.axpages = axpages
        self.rfidx = rfidx
        self.ipage = 0
        self.goodrf = np.ones(opts.evt_num)
        self.lines = [[] for i in range(opts.evt_num)]
        self.wvfillpos = [[] for i in range(opts.evt_num)]
        self.wvfillnag = [[] for i in range(opts.evt_num)]
        self.plotwave()
        self.plotbaz()
        self.fig.suptitle("%s (Latitude: %5.2f\N{DEGREE SIGN}, Longitude: %5.2f\N{DEGREE SIGN})" % (opts.staname, opts.stla, opts.stlo), fontsize=20)
        ax.set_ylim(rfidx[self.ipage][0], rfidx[self.ipage][-1]+2)
        ax.set_yticks(np.arange(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2))
        ylabels = opts.filenames[rfidx[self.ipage][0]::]
        ylabels.insert(0, '')
        ax.set_yticklabels(ylabels)
        ax_baz.set_ylim(ax.get_ylim())
        ax_baz.set_yticks(ax.get_yticks())
        self.azi_label = ['%5.2f' % opts.baz[i] for i in rfidx[self.ipage]]
        self.azi_label.insert(0, "")
        ax_baz.set_yticklabels(self.azi_label)
        self.bnext.on_clicked(self.butnext)
        self.bprevious.on_clicked(self.butprevious)
        self.bfinish.on_clicked(self.finish)
        self.bplot.on_clicked(self.plot)
        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        ax.plot([0, 0], [0, axpages*opts.maxidx], color="black")
        ax.set_xlim(opts.xlim[0], opts.xlim[1])
        ax.set_xticks(np.arange(opts.xlim[0], opts.xlim[1]+1, 2))
        ax_baz.set_xlim(0, 360)
        ax_baz.set_xticks(np.arange(0, 361, 60))

    def finish(self, event):
        opts = self.opts
        badidx = np.where(self.goodrf == 0)[0]
        print("%d RFs are rejected" % len(badidx))
        with open(os.path.join(opts.path, opts.staname+"finallist.dat"), 'w+') as fid:
            for i in range(opts.evt_num):
                evtname = os.path.basename(opts.filenames[i])
                evtname = re.split('[_|.]\w[_|.]',evtname)[0]
                if self.goodrf[i] == 0:
                    os.system("rm -f %s" % os.path.join(opts.path, evtname+'*.sac'))
                    os.system("rm -f %s" % os.path.join(opts.cut_path, evtname+'*.SAC'))
                    print("Reject PRF of "+evtname)
                    continue
                evla = opts.rffiles[i].stats.sac.evla
                evlo = opts.rffiles[i].stats.sac.evlo
                evdp = opts.rffiles[i].stats.sac.evdp
                dist = opts.rffiles[i].stats.sac.gcarc
                baz = opts.rffiles[i].stats.sac.baz
                rayp = opts.rffiles[i].stats.sac.user0
                mag = opts.rffiles[i].stats.sac.mag
                gauss = opts.rffiles[i].stats.sac.user1
                fid.write('%s %s %6.3f %6.3f %6.3f %6.3f %6.3f %8.7f %6.3f %6.3f\n' % (evtname, 'P', evla, evlo, evdp, dist, baz, rayp, mag, gauss))
        shutil.copy(os.path.join(opts.path, opts.staname+"finallist.dat"), os.path.join(opts.cut_path, opts.staname+"finallist.dat"))
        sys.exit(0)

    def onclick(self, event):
        if event.inaxes != self.ax:
            return
        click_idx = int(np.round(event.ydata))
        if click_idx > self.opts.evt_num:
            return
        if self.goodrf[click_idx-1] == 1:
            print("Selected "+os.path.basename(self.opts.filenames[click_idx-1]))
            self.goodrf[click_idx-1] = 0
            self.wvfillpos[click_idx-1].set_facecolor('gray')
            self.wvfillnag[click_idx-1].set_facecolor('gray')
        else:
            print("Canceled "+os.path.basename(self.opts.filenames[click_idx-1]))
            self.goodrf[click_idx-1] = 1
            self.wvfillpos[click_idx-1].set_facecolor('red')
            self.wvfillnag[click_idx-1].set_facecolor('blue')
        plt.draw()

    def plotwave(self):
        ax = self.ax
        opts = self.opts
        bound = np.zeros(opts.RFlength)
        time_axis = np.linspace(opts.b, opts.e, opts.RFlength)
        for i in range(opts.evt_num):
            rf = opts.rffiles[i]
            amp_axis = rf.data*opts.enf+i+1
            self.lines[i], = ax.plot(time_axis, amp_axis, color="black", linewidth=0.2)
            self.wvfillpos[i] = ax.fill_between(time_axis, amp_axis, bound+i+1, where=amp_axis >i+1, facecolor='red', alpha=0.3)
            self.wvfillnag[i] = ax.fill_between(time_axis, amp_axis, bound+i+1, where=amp_axis <i+1, facecolor='blue', alpha=0.3)

    def plotbaz(self):
        self.ax_baz.scatter(self.opts.baz, np.arange(self.opts.evt_num)+1)

    def plot(self, event):
        opts = self.opts
        st = opts.rffiles.copy()
        filenames = opts.filenames.copy()
        print('Plotting Figure of '+opts.staname)
        for i in range(opts.evt_num):
            if self.goodrf[i] == 0:
                filenames.remove(opts.filenames[i])
                st.remove(opts.rffiles[i])
        plotrf.plot_R(st, filenames, opts.image_path, opts.staname)
        print("Figure has saved into %s" % opts.image_path)
        if sys.platform == 'darwin':
            os.system('open %s' % os.path.join(opts.image_path, opts.staname+'_R.ps'))
        elif sys.platform == 'linux':
            os.system('xdg-open %s' % os.path.join(opts.image_path, opts.staname+'_R.ps'))
        else:
            print('Cannot open the .ps file')
        
    def butprevious(self, event):
        opts = self.opts
        ax = self.ax
        ax_baz = self.ax_baz
        self.ipage -= 1
        if self.ipage < 0:
            self.ipage = 0
            return
        ax.set_ylim(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2)
        ax.set_yticks(np.arange(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2))
        ylabels = opts.filenames[self.rfidx[self.ipage][0]::]
        ylabels.insert(0, '')
        ax.set_yticklabels(ylabels)
        ax_baz.set_ylim(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2)
        ax_baz.set_yticks(ax.get_yticks())
        self.azi_label = ['%5.2f' % opts.baz[i] for i in self.rfidx[self.ipage]]
        self.azi_label.insert(0, "")
        ax_baz.set_yticklabels(self.azi_label)
        plt.draw()

    def butnext(self, event):
        opts = self.opts
        ax = self.ax
        ax_baz = self.ax_baz
        self.ipage += 1
        if self.ipage >= self.axpages:
            self.ipage = self.axpages-1
            return
        if self.ipage == self.axpages-1:
            ymax = (self.ipage+1)*opts.maxidx
            ax.set_ylim(self.rfidx[self.ipage][0], ymax)
            ax.set_yticks(np.arange(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2))
            ylabels = opts.filenames[self.rfidx[self.ipage][0]::]
            ylabels.insert(0, '')
            ax.set_yticklabels(ylabels)
            self.azi_label = ['%5.2f' % opts.baz[i] for i in self.rfidx[self.ipage]]
        else:
            ax.set_ylim(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2)
            ax.set_yticks(np.arange(self.rfidx[self.ipage][0], self.rfidx[self.ipage][-1]+2))
            ylabels = opts.filenames[self.rfidx[self.ipage][0]::]
            ylabels.insert(0, '')
            ax.set_yticklabels(ylabels)
            self.azi_label = ['%5.2f' % opts.baz[i] for i in self.rfidx[self.ipage]]
        ax_baz.set_ylim(ax.get_ylim())
        self.azi_label.insert(0, "")
        ax_baz.set_yticklabels(self.azi_label)
        ax_baz.set_yticks(ax.get_yticks())
        plt.draw()

def main():
    opts = initopts.opts()
    opts.maxidx = 20
    opts.enf = 7
    opts.xlim = [-2, 80]
    opts.ylim = [0, 22]
    opts.rffiles, opts.filenames, opts.path, opts.image_path, opts.cut_path, opts.staname = get_sac()
    opts.evt_num = len(opts.rffiles)
    rf = opts.rffiles[0]
    opts.b = rf.stats.sac.b
    opts.e = rf.stats.sac.e
    opts.stla = rf.stats.sac.stla
    opts.stlo = rf.stats.sac.stlo
    opts.RFlength = rf.data.shape[0]
    bazi = [tr.stats.sac.baz for tr in opts.rffiles]
    tmp_filenames = [[opts.filenames[i], bazi[i]] for i in range(opts.evt_num)]
    tmp_filenames = sorted(tmp_filenames, key=itemgetter(1))
    opts.filenames = [file[0] for file in tmp_filenames]
    opts.baz = np.sort(bazi)
    opts.idx_bazi = np.argsort(bazi)
    opts.rffiles = [opts.rffiles[i] for i in opts.idx_bazi]
    plotrffig(opts)


if __name__ == "__main__":
    main()
    plt.show()
