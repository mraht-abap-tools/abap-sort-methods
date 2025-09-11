# Version: 07.09.2025-001

import logging
import re
import os.path as path;

import tkinter as tk 
from tkinter import filedialog

def info(msg):
    logging.info(msg)
    print(msg)
# ENDDEF

def error(msg):
    logging.error(msg)
    print(msg)
# ENDDEF

def inputFileName():
    fileName = '';
    while True:
        fileName = filedialog.askopenfilename(title='Dateiname', filetypes=[('ABAP files', '*.abap *.txt')]);
        if fileName == '':
            exit();
        
        fileName = fileName.translate({ord(i):None for i in '\'"&'}).lstrip();
        if fileName != '' and path.exists(fileName):
            break;
        else:
            print('Please enter a valid file name!');
        #ENDIF
    # ENDWHILE

    return fileName;
# ENDDEF

def readFileLines(fileName):
    fileHandler = open(fileName, "r", errors='ignore');
    fileContent = fileHandler.read();
    fileHandler.flush();
    fileHandler.close();

    return fileContent.splitlines();
# ENDDEF

def extractMethod(fileLines):
    # Extract method names
    newFileContentList = [];
    sectionType = 0;
    methodName = '';
    methodType = '';
    methodIndex = -1;
    methods = [];
    isClassDef = False;
    isClassImp = False;
    isMethodDef = False;
    isMethodImp = False;

    for i, line in enumerate(fileLines):
        if i > 0:
            line = "\n" + line;
        #ENDIF

        if result := re.search(r'(\w+)\s+SECTION', line):
            sectionType += 1;
        elif re.search(r'ENDCLASS', line):
            isClassDef = False;
            isClassImp = False;
        #ENDIF

        if isClassDef == True:
            methods, isMethodDef, methodName, methodType, newFileContentList = detMethodDef(
                line, methods, isMethodDef, sectionType, methodName, methodType, newFileContentList);
        elif isClassImp == True:
            methods, isMethodImp, methodIndex, newFileContentList = detMethodImp(
                line, methods, isMethodImp, methodIndex, newFileContentList);
        else:
            newFileContentList.append(line);
        # ENDIF

        if re.search(r'CLASS[\s\S]*DEFINITION', line):
            isClassDef = True;
        elif re.search(r'CLASS[\s\S]*IMPLEMENTATION', line):
            isClassImp = True;
        # ENDIF
    # ENDFOR

    return methods, newFileContentList;
# ENDDEF


def detMethodDef(line, methods, isMethodDef, sectionType, methodName, methodType, newFileContentList):   
    if re.search('METHODS', line):
        isMethodDef = True;
        methods.append(['', sectionType, '', '']);
        methodName = '';
        if result := re.search(r'METHODS:?\s+(\w+)', line):
            methodName = result.group(1);
        # ENDIF
        if re.search(r'CLASS-METHODS', line):
            methodType = 'CLASS-METHODS';
        elif re.search(r'METHODS', line):
            methodType = 'METHODS';
        # ENDIF
    elif isMethodDef == True and methodName == '':
        if result := re.search(r'\s*(\w+)', line):
            methodName = result.group(1);
        # ENDIF
    # ENDIF

    methodIndex = len(methods) - 1;

    if isMethodDef == True:
        methods[methodIndex][2] += line;
    # ENDIF

    if methodName != '' and methods[methodIndex][0] == '':
        methods[methodIndex][0] = methodName;
    #ENDIF

    isEndOfDef = False;
    if isMethodDef == True and re.search(r',', line):
        isEndOfDef = True;
        methods[methodIndex][2] = methods[methodIndex][2].replace(",", ".");
        methods.append(['', sectionType, '', '']);
    elif isMethodDef == True and re.search(r'.*\.+', line):
        isEndOfDef = True;
        isMethodDef = False;
    # ENDIF

    if isEndOfDef == True:
        if not re.search(r'METHODS', methods[methodIndex][2]):
            result = re.search(r'\w', methods[methodIndex][2]);
            startIndex = result.start();
            methods[methodIndex][2] = methods[methodIndex][2][:startIndex] + \
                methodType + ' ' + methods[methodIndex][2][startIndex:];
        # ENDIF
        methodName = '';
        isEndOfDef = False;
        newFileContentList.append(methods[methodIndex][2]);
    elif isMethodDef == False:
        newFileContentList.append(line);
    # ENDIF

    return methods, isMethodDef, methodName, methodType, newFileContentList;
# ENDDEF


def detMethodImp(line, methods, isMethodImp, methodIndex, newFileContentList):
    # Check if method implementation
    if result := re.search(r'^\s*METHOD\s+(\w+)', line):
        isMethodImp = True;
    # ENDIF

    # Determine method index
    if result != None:
        methodIndex = -1;
        for i, method in enumerate(methods):
            if method[0] == result.group(1):
                methodIndex = i;
                break;
            # ENDIF
        # ENDFOR
    # ENDIF

    if methodIndex > -1 and isMethodImp == True:
        methods[methodIndex][3] += line;
    # ENDIF

    if isMethodImp == True and re.search(r'ENDMETHOD', line):
        isMethodImp = False;
        newFileContentList.append(methods[methodIndex][3]);
    elif isMethodImp == False:
        newFileContentList.append(line);        
    # ENDIF

    return methods, isMethodImp, methodIndex, newFileContentList;
# ENDDEF


def createNewFileContent(newFileContentList, methods):
    newFileContent = '';
    methodIndex = 0;
    # As '_' may be considered appearing before any character the sort order is
    # not identical to the one SAP uses. Thus we temporarily change '_' to '{'
    # which is the first ASCII character after 'z' (7A/122).
    methods = sorted(methods, key=lambda m: (m[1], m[0].lower().replace("_", "{")));

    for line in newFileContentList:
        if re.search(r'METHODS', line):           
            newFileContent += methods[methodIndex][2];
            methodIndex += 1;
        elif re.search(r'^\s*METHOD', line):
            newFileContent += methods[methodIndex][3];
            methodIndex += 1;
        else:
            newFileContent += line;
        # ENDIF

        # First method definitions are built then implementations:
        # * Definitions are being sorted by sections and names
        # * Implementations are being sorted by names only
        if methodIndex == len(methods):
            methodIndex = 0;
            methods = sorted(methods, key=lambda m: m[0].lower().replace("_", "{"));
        #ENDIF
    # ENDFOR

    return newFileContent;
# ENDDEF


def writeNewFileContent(fileName, newFileContent):
    fileNameParts = path.splitext(fileName);
    fileHandler = open(fileNameParts[0] + "_sorted" + fileNameParts[1], "w");
    fileHandler.write(newFileContent);
    fileHandler.flush();
    fileHandler.close();
# ENDDEF

def execute():
    logging.basicConfig(level=logging.DEBUG, filename="log.txt", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s");

    info('************************************* SORT_ABAP_METHODS **************************************');
    print(f"Enter 'quit' or 'STRG+C' to quit\n");

    fileName = inputFileName();

    info('**********************************************************************************************');

    fileLines = readFileLines(fileName);
    methods, newFileContentList = extractMethod(fileLines);
    newFileContent = createNewFileContent(newFileContentList, methods);
    writeNewFileContent(fileName, newFileContent);

    info('Conversion successfully executed.');
    return True;
# ENDDEF

runApp = True;
while runApp == True:
    runApp = execute();