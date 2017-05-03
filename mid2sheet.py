#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# mid2sheet.py
# Midi-Files -> Sheets for Musicbox (30 notes, starting from F)
# (c) 2017 Niklas Kannenberg <kannenberg@airde.net> and Gunnar J.
# Released under the GPL v3 or later, see file "COPYING"
#
#   ToDo
#     - Use 'pypdf' instead of external 'pdfjam' for PDF merging, avoid latex
#       (to much dependencies)
#
#   Bugs
#     - No whitespace in path/to/script allowed
#       pdfjam and rm will not work, see subprocess.call()
#     - exits if input/output folder not exists, better create output folder
#
#
# Useful links:
# https://mido.readthedocs.io/en/latest/midi_files.html
# http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html
# http://stackoverflow.com/questions/3444645/merge-pdf-files
# https://pythonhosted.org/PyPDF2/
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import mido
import os
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import datetime


# version of this software
version            =     0.3

# print lot of debug messages?
debug              =       0

# directories
inputdir           = os.getcwd()+"/input"    # input directory, e.g. "/input"
outputdir          = os.getcwd()+"/output"   # output directory for PDFs

# notes and y_mm
yBase       =   5.5           # y_mm first note
yAbst       =   58.5 / 29.0   # y_mm between notes
yUppr       =   70.0          # y_mm whole strip

# Plot
x8beat      =     4.0         # x_mm per 1/8 beat
minbeat     =     7.9         # minimal playable x-distance for one note
xprmax      =   250.0         # printable size, A4 Landscape
preplt      =     8.0         # space for note names on plot, do not change

# lut midi-note -> y_mm
notemmlut   = [   #  Note       # y_mm                  # name
              [   53,           yBase +  0 * yAbst  ],  #  F

              [   55,           yBase +  1 * yAbst  ],  #  G

              [   60,           yBase +  2 * yAbst  ],  #  C

              [   62,           yBase +  3 * yAbst  ],  #  D

              [   64,           yBase +  4 * yAbst  ],  #  E
              [   65,           yBase +  5 * yAbst  ],  #  F

              [   67,           yBase +  6 * yAbst  ],  #  G

              [   69,           yBase +  7 * yAbst  ],  #  A
              [   70,           yBase +  8 * yAbst  ],  #  A#
              [   71,           yBase +  9 * yAbst  ],  #  H
              [   72,           yBase + 10 * yAbst  ],  #  C
              [   73,           yBase + 11 * yAbst  ],  #  C#
              [   74,           yBase + 12 * yAbst  ],  #  D
              [   75,           yBase + 13 * yAbst  ],  #  D#
              [   76,           yBase + 14 * yAbst  ],  #  E
              [   77,           yBase + 15 * yAbst  ],  #  F
              [   78,           yBase + 16 * yAbst  ],  #  F#
              [   79,           yBase + 17 * yAbst  ],  #  G
              [   80,           yBase + 18 * yAbst  ],  #  G#
              [   81,           yBase + 19 * yAbst  ],  #  A
              [   82,           yBase + 20 * yAbst  ],  #  A#
              [   83,           yBase + 21 * yAbst  ],  #  H
              [   84,           yBase + 22 * yAbst  ],  #  C
              [   85,           yBase + 23 * yAbst  ],  #  C#
              [   86,           yBase + 24 * yAbst  ],  #  D
              [   87,           yBase + 25 * yAbst  ],  #  D#
              [   88,           yBase + 26 * yAbst  ],  #  E
              [   89,           yBase + 27 * yAbst  ],  #  F

              [   91,           yBase + 28 * yAbst  ],  #  G

              [   93,           yBase + 29 * yAbst  ],  #  A
              ]

print("-> Converting .mid to .pdf for Musicbox  -  mid2sheet v"+str(version))
print("--------------------------------------------------------")
print("Input from Folder: "+inputdir)
print("Output  to Folder: "+outputdir)


# midi note number to y_mm
def get_mm(note):
    retval = -1
    for i in range(len(notemmlut)):
        if (notemmlut[i][0] == note):
            retval = notemmlut[i][1]
    return retval


# name of midi note number
def get_name(note):
    names = [ "C","C#","D","D#","E","F","F#","G","G#","A","A#","H" ]
    return names[note % 12]


# returns 1 if note is to close to last note on same line
def get_terr(notes, pos):
    gap = 9999
    for i in range(0,pos):
        if(notes.note[i] == notes.note[pos]):
            gap = notes.x[pos] - notes.x[i]
    if(gap < minbeat): # gap < min_gap
        return 1 # not playable
    else:
        return 0 # OK

# mm -> inch (for matplotlib)
def mm2in(mm):
    return mm/10/2.54  # mm to inch


# convert one midi file
def do_convert(infile, outfile, fname):

    mid        = mido.MidiFile(infile)      # the input file
    now        = datetime.datetime.now()    # actual time
    sig_cnt    = 0                          # counter for signature messages
    tim_cnt    = 0                          # counter for timing messages

    # midi timing ticks per beat
    ticks_4th  = mid.ticks_per_beat
    ticks_8th  = ticks_4th / 2

    # data frame for all midi events of melody track
    datacols   = ['time','tdiff','type','track','bytes']
    data       = pd.DataFrame(columns=datacols)

    # data frame for note_on events
    notecols   = ['time','note','name', 'x', 'y', 'bar']
    notes      = pd.DataFrame(columns=notecols)

    # list all tracks
    if(debug):
        print("Tracks  : " + str(len(mid.tracks)))
        for i in range(len(mid.tracks)):
            track_len = len(mid.tracks[i])
            print("Track " + str(i) + " : " + str(track_len) + " events")


    # extract all messages from all tracks to data frame 'data'
    for i, track in enumerate(mid.tracks):

        for msg in track:

            if(msg.type == "time_signature"):
                time_signature = msg.dict()
                numerator = time_signature['numerator']
                denominator = time_signature['denominator']
                sig_cnt += 1
                if(debug):
                    print("Timing  : " + str(numerator) + "/" + str(denominator))


            if(msg.type == "set_tempo"):
                set_tempo = msg.dict()
                tempo = round((500000 / set_tempo['tempo']) * 120, 2)
                tim_cnt += 1
                if(debug):
                    print("Tempo   : " + str(tempo) + " bpm")


            data = data.append({ 'time'  : 0,
                                 'tdiff' : msg.time,
                                 'type'  : msg.type,
                                 'track' : i,
                                 'bytes' : msg.bytes()  }, ignore_index=True)

    # warnings for tracks, tempo and signature
    if(len(mid.tracks) != 1):
        print("-> WARNING: Midi file has " + str(len(mid.tracks)) + " tracks instead of 1")
    if(sig_cnt != 1):
        print("-> WARNING: Midi file has " + str(sig_cnt) + " signature messages instead of 1. " +
              "Using " + str(numerator) + "/" + str(denominator))
    if(tim_cnt != 1):
        print("-> WARNING: Midi file has " + str(tim_cnt) + " tempo messages instead of 1. " +
              "Using " + str(tempo) + " bpm.")


    # calculate absolute timing values
    for i in range(1, len(data)):
        # actual time difference
        tdiffnext = data.tdiff[i]
        # accumulate time only for same track
        if(data.track[i] == data.track[i-1]):
            timeacc   = data.time[i-1]
        else:
            timeacc   = 0
        data.loc[i, 'time'] = timeacc + tdiffnext


    # extract all 'note_on' events from 'data' to 'notes
    for i in range(len(data)):
       #         event == note_on   AND         velocity > x
       if(data.type[i] == 'note_on' and data.bytes[i][2] > 0):

         thisnote  = data.bytes[i][1]
         mtime = data.time[i]
         x_val = ( mtime / ticks_8th ) * x8beat

         notes = notes.append({ 'time' : data.time[i],
                                'note' : thisnote,
                                'name' : get_name(thisnote),
                                'x'    : x_val,
                                'y'    : get_mm(thisnote),
                                'bar'  : (data.time[i] /
                                         (4 * ticks_4th * (numerator/denominator))) + 1
                              }, ignore_index=True)

    # mm per bar
    mm_bar = 8 * x8beat * (numerator/denominator)
    # bars per page
    bars_pp = int((xprmax - preplt) / mm_bar)

    # debug
    if(debug):
        #print("--- DATA ---")
        #print(data)
        print("--- NOTES ---")
        print(notes)


    # generate plot
    # -----------------------------

    # size of one strip
    strip_x  = mm2in(preplt + bars_pp * mm_bar) # X-Size of plot
    strip_y  = mm2in(yUppr)                     # Y-Size of plot
    hlines_x = mm2in(preplt)  # start of horizontal note lines
    newpage = 1  # flag for newpage
    pagecnt = 0  # page counter
    poffs   = 0  # x-offset for current page

    # for all notes  (can't manipulate k in 'for' loop but in 'while' loop)
    k = 0
    while(k < len(notes) ):

      # create a new plot
      if( newpage==1 ):

        newpage = 0            # reset flag
        pagecnt = pagecnt + 1  # increment page counter

        if(pagecnt > 1):       # re plot last notes on current page
          while( (notes.bar[k] ) >=  bars_pp * (pagecnt - 1) + 1 ):
            k -= 1
          k += 1 # undo last while, no 'do-while' loop in python


        # frame line width, hacked
        plt.rcParams['axes.linewidth'] = 0.2

        # x-offset for this page
        poffs = mm2in( -preplt + (pagecnt-1) * mm_bar * bars_pp )

        # create figure
        f  = plt.figure(figsize=(strip_x,strip_y), dpi=300,frameon=False)
        ax = plt.subplot(111)
        # figure has no borders
        plt.subplots_adjust(left=0,right=1,bottom=0,top=1)

        # plot 30 horizontal lines
        for i in range(len(notemmlut)):

          yy = mm2in(notemmlut[i][1]) # y-val
          nnote = get_name(notemmlut[i][0])  # name of the acutal note

          if(nnote == "C"):          #  C-Lines
            plt.plot([hlines_x,strip_x],[yy,yy],color="black", linewidth=0.4)
          elif nnote.endswith("#"):  # #-Lines (Black keys)
            plt.plot([hlines_x,strip_x],[yy,yy],color="black", linewidth=0.1, linestyle=':')
          else:                      # Normal Lines
            plt.plot([hlines_x,strip_x],[yy,yy],color="black", linewidth=0.2)

          # add the name of the note
          if(i%2 ==0): ofs = 0.1    # indent every 2nd note
          else:        ofs = 0.0    # no indent
          ax.text(.1+ofs,yy, nnote, fontsize=5,verticalalignment='center',rotation=90)

        # plot beat lines
        for i in range(bars_pp * numerator):
          xx = mm2in(mm_bar) / numerator # x per bar
          if(i % numerator == 0):
            # plot line (full bar)
            plt.plot([hlines_x+xx*i, hlines_x+xx*i ],
                     [mm2in(notemmlut[0][1]), mm2in(notemmlut[-1][1])],color="black",linewidth=0.4)
            # plot bar number
            ax.text( hlines_x+xx*i + (xx/2), mm2in(notemmlut[0][1]) - mm2in(2.5),
                   str(int(1+ i/numerator + bars_pp * (pagecnt-1))),
                   fontsize=5,horizontalalignment='center',)
          else:
            # plot line (beat)
            plt.plot([hlines_x+xx*i, hlines_x+xx*i ],
                     [mm2in(notemmlut[0][1]), mm2in(notemmlut[-1][1])],
                      color="black",linewidth=0.1, linestyle=':')

        # add song name and info
        ax.text( hlines_x + mm2in(4), yy + mm2in(2),
                 str(pagecnt) + "     " + fname + "       " +
                 str(numerator) + "/" + str(denominator) + "   " + str(tempo) + " bpm",
                 fontsize=8, horizontalalignment='left')
        ax.text( mm2in(xprmax) / 2, yy + mm2in(2),
                 "Generated in " + now.strftime('%Y-%m-%d') +
                 " with mid2sheet v" + str(version)  ,
                 fontsize=5, horizontalalignment='left')

        # vertical start line
        plt.plot([hlines_x,hlines_x],[0,strip_y],color="black", linewidth=0.4)
        plt.xticks([])
        plt.yticks([])
        ax.axis([0,strip_x, 0, strip_y])

      # end if newpage

      # position of note to plot
      xx = mm2in(notes.x[k])
      yy = mm2in(notes.y[k])
      xx = xx -poffs

      # plot one note
      if(notes.y[k] != -1): # normal note
        plt.plot(xx,yy,marker='.',color='white',markersize=12)
        plt.plot(xx,yy,marker='.',color='black',markersize=8)
        plt.plot(xx,yy,marker='.',color='white',markersize=5)
        # fill red, if timing is to short
        if(get_terr(notes, k)):
          plt.plot(xx,yy,marker='.',color='red',markersize=3)
      else: # plot error note name (not in musicbox range)
        ax.text( xx,mm2in(1),get_name(int(notes.note[k])),
                 fontsize=5,color='red', horizontalalignment='center',)

      # prepare new page, if this note was already outside current page
      if( (notes.bar[k] ) >  bars_pp * pagecnt + 1  ):
        newpage = 1
        # save current page to file
        filename = outfile + "_%03d" % (pagecnt) + '.pdf'
        f.savefig(filename, bbox_inches='tight')
      # next note (manually in while loop)
      else:
        k += 1

      # for all notes

    # save last page to file
    filename = outfile + "_%03d" % (pagecnt) + '.pdf'
    f.savefig(filename, bbox_inches='tight')

    # combine pdfs, TODO: switch to PyPDF2
    subprocess.call("pdfjam " + outfile  + "_*.pdf  --nup 1x2 --a4paper --landscape  --noautoscale true --delta '0.5cm 0.5cm'  --outfile " + outfile + ".pdf", shell=True)
    subprocess.call("rm " + outfile  + "_*.pdf ", shell=True)

    # result: list of notes with x,y mm values
    return notes



# convert all files
for filename in os.listdir(inputdir):

    if filename.endswith(".mid"):

        inpfile      = inputdir+"/"+filename

        outfile_name = filename.rsplit('.', 1)[0]
        outfile      = outputdir+"/"+outfile_name

        print("--------------------------------------------------------")
        print("-> Input File  : "+filename)
        print("-> Output File : "+outfile_name + ".pdf")

        do_convert(inpfile, outfile, outfile_name)


print("--------------------------------------------------------")
print("DONE")
