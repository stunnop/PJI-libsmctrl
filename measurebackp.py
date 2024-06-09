import subprocess
import time
import csv
import argparse
import os
import shutil

NB_TPC= 7
parts_T1000 = ["1-1", "1-2", "1-3", "1-4","1-5","1-6","1-7"]
benchmark_EXE = "./gaussian -s 2000"

def main(compiled_source, output_csv, kernels):
    #init output file
    with open(output_csv, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Exe","TPCS" ,"Average Completion Time (seconds)"])
    
    times = []
    #kernels = " ".join(kernels)
    backup_source = compiled_source + '.old'
    source_dir = os.path.dirname(compiled_source)
    # Create a backup by copying the file to the .old file
    if not os.path.exists(backup_source):
        shutil.copyfile(compiled_source, backup_source)
    else:
        print(".old source file found, backup will be used. ")
        shutil.copyfile(backup_source, compiled_source)
    
    time_per_part = []
    for partition in parts_T1000:
        parts = [f"{kernels[i]}:{partition}" for i in range(0, len(kernels))]
        parts = " ".join(parts)
        cmd = f"python3 partition.py {backup_source} -k {parts} -o partitioned.cu"
        print(cmd)
        time.sleep(2)
        subprocess.run(cmd, shell=True)
        #after reading backup source, replace the compiled file it with the partitioned version
        shutil.copyfile("partitioned.cu", compiled_source)
        subprocess.run("make clean",shell=True,cwd=source_dir)
        make_res = subprocess.run("make",shell=True, cwd=source_dir)
        results = []
        for i in range (10):
            start_time = time.time()
            result = subprocess.run(benchmark_EXE,shell=True, cwd=source_dir)
            end_time = time.time()
            results.append(end_time-start_time)
        average_time = sum(results)/len(results)
        with open(output_csv, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([benchmark_EXE, partition,average_time])
    
    
    exit(1)

    #-------------------------------------------
    for i in range(10):
        completion_time = run_binary(binary_path, binary_args)
        times.append(completion_time)
        print(f"Run {i + 1}: {completion_time:.4f} seconds")

    average_time = sum(times) / len(times)
    print(f"Average completion time: {average_time:.4f} seconds")

    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Run", "Average Completion Time (seconds)"])
        writer.writerow([binary_dir, average_time])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a binary executable multiple times and measure the average completion time.")
    parser.add_argument('partition_source', type=str, help='Input file path')
    parser.add_argument("--output_csv", type=str, default="partition_performance.csv", help="The output CSV file name.")
    parser.add_argument('-k', '--kernels', nargs='+', help='Specify name and desired partitioning of kernels. kernel_name:1-4 = assign to tpcs 1 through 4 (inclusive)', required=True)
    args = parser.parse_args()

    main(args.partition_source, args.output_csv, args.kernels)
