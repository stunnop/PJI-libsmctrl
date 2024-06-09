import argparse
import re
"""
This program does not check your assignements, i.e assigning sms that do not exist, etc.
It simply inserts the masks you specified with your arguments into your chosen source file. 

In the case of multiple calls to the same kernel, the mask will be set for each call. 
"""

#templates for calling the libsmctrl API
class libsm:
    GLOBAL = "libsmctrl_set_global_mask({mask})"
    STREAM = "libsmctrl_set_stream_mask({stream},{mask})"
    NEXT = "libsmctrl_set_next_mask({mask})"

def printwarning(*args, **kwargs):
    print("\n---> WARNING : ", end='')
    print(*args, **kwargs)
    print("")

def keep_whitespace_only(input_string):
    # Use regular expression to remove non-whitespace characters
    input_string = input_string.rstrip()
    return re.search(r'^\s+', input_string).group()
    #return re.sub(r'\S', '', input_string)

def get_kernel_name(input_string):
    # Define the regular expression pattern to include underscores
    pattern = r'([\w_]+)\s*<<<'
    # Use re.search to find the first match of the pattern
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)
    else:
        return ''


"""
Takes the TPC numbers we want to allow, and returns the string 
(representing the correct mask) to be written in the source cuda program
Ex : 
Input TPCs 1 & 2 (011)
Output "~0x3ull"
"""
def create_mask(sm_nums):
    result = 0
    sm_nums = [x - 1 for x in sm_nums] #sm nums start at 1, bits idxs at 0
    #set bits representing sm numbers to 1
    for index in sm_nums:
        result |= (1 << index )
    
    return f"~{hex(result)}ull"


"""
expects formats :

kernel_name:1-4 = assign to tpcs 1 through 4 (inclusive)
kernel_name:1,4 = assign to tpcs 1 & 4
kernel_name:4 kernel_name:3 etc

output : dict[name_of_kernel] = calculated_mask
"""
def parse_partitioning(args):
    names = []
    tpcs = []
    try:
        for k in args:
            assignment = k.split(':')
            names.append(assignment[0])
            if('-' in assignment[1]):
                tmp = assignment[1].split('-')
                if len(tmp) > 2 : raise Exception("bad argument : range can only have 2 values, beginning and end")
                tmp = [int(x) for x in tmp]
                if(tmp[1] < tmp[0]) : raise Exception("bad argument :  in range x-y, y should be larger than x.")
                tpcs.append([x for x in range( tmp[0], tmp[1]+1 )])
            elif (',' in assignment[1]):
                tmp = assignment[1].split(',')
                tmp = [int(x) for x in tmp]
                tpcs.append(tmp)
            else:
                tpcs.append([int(assignment[1])])
            
        masks = [create_mask(tpc) for tpc in tpcs]
        print(names, masks)
        return dict(zip(names, masks))
    except Exception as e:
        print("ERROR : Incorrectly formatted arguments, try again. ")
        print(e)
        exit(1)


def main():
    parser = argparse.ArgumentParser(description="Apply TPC/SM masks from the libsmctrl library to cuda kernels. This program does not check your assignements, i.e assigning sms that do not exist, etc. \n It simply calculates and inserts the masks you specified with your arguments into your chosen source file. \n It does this by finding kernel launches (\"<<<\") and sticking a next_mask(yourmask) in front of them. ")
    parser.add_argument('input_file', type=str, help='Input file path')
    parser.add_argument('-o', '--output_file', type=str, default='output.cu', help='Output file path (default: output.cu)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-k', '--kernels', nargs='+', help='Specify name and desired partitioning of kernels. Accepted Formats:\n kernel_name:1-4 = assign to tpcs 1 through 4 (inclusive) \nkernel_name:1,4 = assign to tpcs 1 & 4 \nkernel_name:4 kernel_name:3 ...', required=True)
    parser.add_argument('-g', '--global', action='store_true', help='Add a default global mask that disables all TPCs but one, or internal kernels may interfere with your partitions. Global masks are only available for cuda versions >= 10.2')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    args = parser.parse_args()
    
    # Access the arguments
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")
    print(f"Verbose: {args.verbose}")
    
    #we could make a class to contain info on the kernels instead of double-dict but hey
    kernel_dict = parse_partitioning(args.kernels)
    kernels_found = {key: False for key in kernel_dict}
    
    if args.verbose:
        def verboseprint(*args, **kwargs):
            print(*args, **kwargs)
    else:   
        verboseprint = lambda *a: None      # do-nothing function
    


#TODO redo all of this. insert a new line instead of this convoluted rubbish NOT : this is not actually possible, since we can have multiple kernels inline that need to be
#masked immediately before their statement
# il faudrait un peu un vrai parseur pr gerer les commentaires multi-ligne, plusieurs comment par statement par exemple
#

    with open(args.input_file, 'r') as file, open(args.output_file, 'w') as outfile:
        linenum = 0
        totalLines = 0
        inCommentBlock = False
        inCommentLine = False
        lines = file.readlines(8000)#read lines in batches of 8000 bytes
        outfile.write("#include <libsmctrl.h>\n")
        #on declare une classe afin de set global mask avant toute fonction appelée (et sans devoir parser pour chercher le main)
        outfile.write(
        "// Use a constructor to call set_global_mask before any kernels can be launched\n"
        "class GlobalMaskSetter {\n"
        "public:\n"
        "    GlobalMaskSetter() { \n"
        "        libsmctrl_set_global_mask(~0x1ull);\n"
        "    }\n"
        "};\n"
        "GlobalMaskSetter setter;\n")
        
        while(lines):
            for line in lines:
                inCommentLine = False
                statements = line.split(';')
                new_statements = []
                for x in range(0, len(statements)):
                    #are we entering of exiting a comment block ?
                    #TODO this system does not account for multiple comment declarations in the same statement
                    #i.e : /*comment*/ /* <<<kernel launch>>>; in this statement, kernel launch will not be considered a comment
                    #we're just hoping that won't happen for now. 
                    #and it might not matter if we set a mask for a commented launch, since it will be overridden at the next real launch ? probably
                    if("//" in statements[x]):
                        if(inCommentLine) :
                            pass
                        else:
                            inCommentLine = True
                    if("/*" in statements[x]):
                        if(inCommentBlock) :
                            pass
                        else:
                            inCommentBlock = True
                    if(("*/") in statements[x]):
                        if(inCommentBlock) :
                            inCommentBlock = False
                        else:
                            pass

                    if "<<<" in statements[x] and not (inCommentBlock or inCommentLine) and get_kernel_name(statements[x]) in kernel_dict:
                        kname = get_kernel_name(statements[x])
                        kernels_found[kname] = True
                        verboseprint(f"kernel call {kname} found, line {linenum}\n")
                        verboseprint(statements[x].strip(), "\n")
                        new_statements.append(keep_whitespace_only(statements[x]) + libsm.NEXT.format(mask=kernel_dict[kname]))#on garde l'indent pr que ce soit beau
                        new_statements.append(statements[x].strip())
                    else:
                        new_statements.append(statements[x])
                
                lines[linenum] = ";".join(new_statements)   
                linenum = linenum + 1
            outfile.writelines(lines)
            lines = file.readlines(8000)
            totalLines = totalLines + linenum
            linenum = 0
        print("Done.")
        print(f"Parsed {totalLines} lines. ")
        notfound = [ name for name,found in kernels_found.items() if found==False]
        if(notfound != []) : printwarning(f"Couldn't find kernels { notfound }")
    
if __name__ == "__main__":  
    main()
