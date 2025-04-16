import re, os.path as path;

def readFileLines(fileName):
    fileHandler = open(fileName, "r");
    fileContent = fileHandler.read();
    fileHandler.flush();
    fileHandler.close();

    return fileContent.splitlines();
# ENDDEF

#TODO Consider sections in definition part
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

        if result := re.search('(\w+)\s+SECTION', line):
            sectionType += 1;
        elif re.search('ENDCLASS', line):
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

        if re.search('CLASS[\s\S]*DEFINITION', line):
            isClassDef = True;
        elif re.search('CLASS[\s\S]*IMPLEMENTATION', line):
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
        if result := re.search('METHODS:?\s+(\w+)', line):
            methodName = result.group(1);
        # ENDIF
        if re.search('CLASS-METHODS', line):
            methodType = 'CLASS-METHODS';
        elif re.search('METHODS', line):
            methodType = 'METHODS';
        # ENDIF
    elif isMethodDef == True and methodName == '':
        if result := re.search('\s*(\w+)', line):
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
    if isMethodDef == True and re.search(',', line):
        isEndOfDef = True;
        methods[methodIndex][2] = methods[methodIndex][2].replace(",", ".");
        methods.append(['', sectionType, '', '']);
    elif isMethodDef == True and re.search('.*\.+', line):
        isEndOfDef = True;
        isMethodDef = False;
    # ENDIF

    if isEndOfDef == True:
        if not re.search('METHODS', methods[methodIndex][2]):
            result = re.search('\w', methods[methodIndex][2]);
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
    if result := re.search('^\s*METHOD\s+(\w+)', line):
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

    if isMethodImp == True and re.search('ENDMETHOD', line):
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
        if re.search('METHODS', line):           
            newFileContent += methods[methodIndex][2];
            methodIndex += 1;
        elif re.search('^\s*METHOD', line):
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


fileName = '';
while True:
    fileName = input('Dateiname: ');
    fileName = fileName.translate({ord(i):None for i in '\'"&'}).lstrip();
    if fileName != '' and path.exists(fileName):
        break;
    else:
        print('Please enter a valid file name!');
    #ENDIF
# ENDWHILE

fileLines = readFileLines(fileName);
methods, newFileContentList = extractMethod(fileLines);
newFileContent = createNewFileContent(newFileContentList, methods);
writeNewFileContent(fileName, newFileContent);

print('Conversion successfully executed.');