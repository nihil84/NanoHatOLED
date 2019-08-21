#!/usr/bin/env python
#
# BakeBit example for the basic functions of BakeBit 128x64 OLED (http://wiki.friendlyarm.com/wiki/index.php/BakeBit_-_OLED_128x64)
#
# The BakeBit connects the NanoPi NEO and BakeBit sensors.
# You can learn more about BakeBit here:  http://wiki.friendlyarm.com/BakeBit
#
# Have a question about this example?  Ask on the forums here:  http://www.friendlyarm.com/Forum/
#
'''
## License

The MIT License (MIT)

BakeBit: an open source platform for connecting BakeBit Sensors to the NanoPi NEO.
Copyright (C) 2016 FriendlyARM

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

BAKEBIT_PATH='../BakeBit/Software/Python'

import sys
sys.path.insert(1, BAKEBIT_PATH)

import bakebit_128_64_oled as oled
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import time
import subprocess
import threading
import signal
import os
import socket

width = 128
height = 64

showPageIndicator = False
pageCount = 2
done = False

oled.init()  #initialze SEEED OLED display
oled.setNormalDisplay()      #Set display to normal mode (i.e non-inverse mode)
oled.setHorizontalMode()

image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)

drawing = False
lock = threading.Lock()

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class Command(object):
    def __init__(self, backPage):
        self.backPage = backPage

    def run(self):
        pass

class HaltSystem(Command):
    def run(self):
        global oled
        switchPage(shutdownPage)
        time.sleep(1)
        print 'Executing POWEROFF'
        os.system('systemctl poweroff')

class RebootSystem(Command):
    def run(self):
        global oled
        switchPage(shutdownPage)
        time.sleep(1)
        print 'Executing REBOOT'
        os.system('systemctl reboot')

class Page(object):
    pageCount = 0
    fontb24 = ImageFont.truetype(BAKEBIT_PATH + '/DejaVuSansMono-Bold.ttf', 24);
    font14 = ImageFont.truetype(BAKEBIT_PATH + '/DejaVuSansMono.ttf', 14);
    smartFont = ImageFont.truetype(BAKEBIT_PATH + '/DejaVuSansMono-Bold.ttf', 10);
    fontb14 = ImageFont.truetype(BAKEBIT_PATH + '/DejaVuSansMono-Bold.ttf', 14);
    font11 = ImageFont.truetype(BAKEBIT_PATH + '/DejaVuSansMono.ttf', 11);

    def __init__(self, showPageIndicator):
        if showPageIndicator:
            self.showPageIndicator = True
            self.page_index = Page.pageCount
            Page.pageCount += 1
            print type(self).__name__ + ": " + str(self.page_index) + " of " + str(Page.pageCount)
        else:
            self.showPageIndicator = False

    def setNextPage(self, nextPage):
        self.nextPage = nextPage

    def draw(self):
        global drawing
        global oled
        global width
        global height
        global image
        global draw

        lock.acquire()
        if drawing:
            lock.release()
            return
        drawing = True
        lock.release()
        
        # Draw a black filled box to clear the image.            
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        
        # Call specific draw of the subclass
        self._doDraw()

        if self.showPageIndicator:
            self._drawPageIndicator(draw)
    
        oled.drawImage(image)

        lock.acquire()
        drawing = False
        lock.release()

    def _drawPageIndicator(self, painter): 
        global width
        global height
        dotWidth=4
        dotPadding=2
        dotX=width-dotWidth-1
        #dotTop=(height-pageCount*dotWidth-(pageCount-1)*dotPadding)/2
        dotTop=0
        for i in range(self.pageCount):
            if i==self.page_index:
                painter.rectangle((dotX, dotTop, dotX+dotWidth, dotTop+dotWidth), outline=255, fill=255)
            else:
                painter.rectangle((dotX, dotTop, dotX+dotWidth, dotTop+dotWidth), outline=255, fill=0)
            dotTop=dotTop+dotWidth+dotPadding

    def onModePressed(self):
        print 'switching from ' + type(self).__name__ + ' to ' + type(self.nextPage).__name__
        switchPage(self.nextPage)

    def onOkPressed(self):
        pass

    def onSelectPressed(self):
        pass

class ClockPage(Page):
    def _doDraw(self):
        text = time.strftime("%A")
        draw.text((2,2),text,font=self.font14,fill=255)
        text = time.strftime("%e %b %Y")
        draw.text((2,18),text,font=self.font14,fill=255)
        text = time.strftime("%X")
        draw.text((2,40),text,font=self.fontb24,fill=255)

class DiagnosticsPage(Page):
    def _doDraw(self):
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0
	IPAddress = get_ip()
        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell = True )
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell = True )
        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell = True )
        tempI = int(open('/sys/class/thermal/thermal_zone0/temp').read());
        if tempI>1000:
            tempI = tempI/1000
        tempStr = "CPU TEMP: %sC" % str(tempI)

        draw.text((x, top+5),       "IP: " + str(IPAddress),  font=self.smartFont, fill=255)
        draw.text((x, top+5+12),    str(CPU), font=self.smartFont, fill=255)
        draw.text((x, top+5+24),    str(MemUsage),  font=self.smartFont, fill=255)
        draw.text((x, top+5+36),    str(Disk),  font=self.smartFont, fill=255)
        draw.text((x, top+5+48),    tempStr,  font=self.smartFont, fill=255)

class SystemPage(Page):
    def __init__(self, showPageIndicator):
        super(SystemPage, self).__init__(showPageIndicator)
        self.selection = 0
        self.haltCommand = HaltSystem(self)
        self.rebootCommand = RebootSystem(self)

    def _doDraw(self):
        draw.text((2, 2),  'System',  font=self.fontb14, fill=255)
        
        reboot_bg = 255 if self.selection==0 else 0
        reboot_fg = 0 if self.selection==0 else 255
        halt_bg = 255 if self.selection==1 else 0
        halt_fg = 0 if self.selection==1 else 255

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=reboot_bg)
        draw.text((4, 22),  'Reboot',  font=self.font11, fill=reboot_fg)

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=halt_bg)
        draw.text((4, 40),  'Halt',  font=self.font11, fill=halt_fg)

    def onModePressed(self):
        self.selection = 0
        super(SystemPage, self).onModePressed()
    
    def onSelectPressed(self):
        self.selection = 1 if self.selection==0 else 0
        self.draw()

    def onOkPressed(self):
        global confirmPage
        confirmPage.setCommand(self.rebootCommand if self.selection==0 else self.haltCommand)
        switchPage(confirmPage)

class ConfirmPage(Page):
    def __init__(self):
        super(ConfirmPage, self).__init__(False)
        self.selection = 0

    def _doDraw(self):
        draw.text((2, 2),  'Confirm?',  font=self.fontb14, fill=255)

        no_bg = 255 if self.selection==0 else 0
        no_fg = 0 if self.selection==0 else 255
        yes_bg = 255 if self.selection==1 else 0
        yes_fg = 0 if self.selection==1 else 255

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=yes_bg)
        draw.text((4, 22),  'Yes',  font=self.font11, fill=yes_fg)

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=no_bg)
        draw.text((4, 40),  'No',  font=self.font11, fill=no_fg)

    def setCommand(self, command):
        self.command = command

    def onModePressed(self):
        pass

    def onSelectPressed(self):
        self.selection = 1 if self.selection==0 else 0
        self.draw()

    def onOkPressed(self):
        if self.selection==1:
            self.command.run()
        else:
            switchPage(self.command.backPage)

class ShutdownPage(Page):
    def __init__(self):
        super(ShutdownPage, self).__init__(False)

    def _doDraw(self):
        draw.text((2, 2),  'Shutting down',  font=self.fontb14, fill=255)
        draw.text((2, 20),  'Please wait',  font=self.font11, fill=255)
    
    def onModePressed(self):
        pass

def draw_page():
    global drawing
    global image
    global draw
    global oled
    global font
    global font14
    global smartFont
    global width
    global height
    global pageCount
    global pageIndex
    global showPageIndicator
    global width
    global height
    global lock

    lock.acquire()
    is_drawing = drawing
    page_index = pageIndex
    lock.release()

    if is_drawing:
        return

    lock.acquire()
    drawing = True
    lock.release()
    
    # Draw a black filled box to clear the image.            
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    # Draw current page indicator
    if showPageIndicator:
        dotWidth=4
        dotPadding=2
        dotX=width-dotWidth-1
        dotTop=(height-pageCount*dotWidth-(pageCount-1)*dotPadding)/2
        for i in range(pageCount):
            if i==page_index:
                draw.rectangle((dotX, dotTop, dotX+dotWidth, dotTop+dotWidth), outline=255, fill=255)
            else:
                draw.rectangle((dotX, dotTop, dotX+dotWidth, dotTop+dotWidth), outline=255, fill=0)
            dotTop=dotTop+dotWidth+dotPadding

    if page_index==0:
        text = time.strftime("%A")
        draw.text((2,2),text,font=font14,fill=255)
        text = time.strftime("%e %b %Y")
        draw.text((2,18),text,font=font14,fill=255)
        text = time.strftime("%X")
        draw.text((2,40),text,font=fontb24,fill=255)
    elif page_index==1:
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 1
        top = padding
        bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0
	IPAddress = get_ip()
        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell = True )
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell = True )
        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell = True )
        tempI = int(open('/sys/class/thermal/thermal_zone0/temp').read());
        if tempI>1000:
            tempI = tempI/1000
        tempStr = "CPU TEMP: %sC" % str(tempI)

        draw.text((x, top+5),       "IP: " + str(IPAddress),  font=smartFont, fill=255)
        draw.text((x, top+5+12),    str(CPU), font=smartFont, fill=255)
        draw.text((x, top+5+24),    str(MemUsage),  font=smartFont, fill=255)
        draw.text((x, top+5+36),    str(Disk),  font=smartFont, fill=255)
        draw.text((x, top+5+48),    tempStr,  font=smartFont, fill=255)
    elif page_index==3: #shutdown -- no
        draw.text((2, 2),  'Shutdown?',  font=fontb14, fill=255)

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=0)
        draw.text((4, 22),  'Yes',  font=font11, fill=255)

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=255)
        draw.text((4, 40),  'No',  font=font11, fill=0)

    elif page_index==4: #shutdown -- yes
        draw.text((2, 2),  'Shutdown?',  font=fontb14, fill=255)

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=255)
        draw.text((4, 22),  'Yes',  font=font11, fill=0)

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=0)
        draw.text((4, 40),  'No',  font=font11, fill=255)

    elif page_index==5:
        draw.text((2, 2),  'Shutting down',  font=fontb14, fill=255)
        draw.text((2, 20),  'Please wait',  font=font11, fill=255)

    oled.drawImage(image)

    lock.acquire()
    drawing = False
    lock.release()


def process_button(signum, stack):
    lock.acquire()
    page = currentPage
    lock.release()

    if signum == signal.SIGUSR1:
        print 'MODE pressed'
        page.onModePressed()
    if signum == signal.SIGUSR2:
        print 'SELECT pressed'
        page.onSelectPressed()
    if signum == signal.SIGALRM:
        print 'OK pressed'
        page.onOkPressed()

def exit_gracefully(signum, stack):
    global done
    done = True

diagnosticsPage = DiagnosticsPage(True)
systemPage = SystemPage(True)
confirmPage = ConfirmPage()
shutdownPage = ShutdownPage()

diagnosticsPage.setNextPage(systemPage)
systemPage.setNextPage(diagnosticsPage)

currentPage = diagnosticsPage

image0 = Image.open(BAKEBIT_PATH + '/friendllyelec.png').convert('1')
oled.drawImage(image0)
time.sleep(2)

signal.signal(signal.SIGUSR1, process_button)
signal.signal(signal.SIGUSR2, process_button)
signal.signal(signal.SIGALRM, process_button)
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

def switchPage(page):
    global currentPage

    lock.acquire()
    currentPage = page
    lock.release()

    page.draw()

while not done:
    try:
        lock.acquire()
        page = currentPage
        lock.release()

        page.draw()

    except KeyboardInterrupt:                                                                                                          
        break                     
    except IOError:
        print ("Error")

oled.clearDisplay()
