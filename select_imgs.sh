#! /bin/bash

# Copyright [2020] Luis Alberto Pineda Cortés, Gibrán Fuentes Pineda,
# Rafael Morales Gamboa.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

runs_dir='runs'
imag_dir="${runs_dir}/images"
test_dir="${imag_dir}/test"
mems_dir="${imag_dir}/memories"

#if [ "$#" -ne 2 ]; then
#    echo "Usage: $0 exp_id stage-id.txt"
#    echo "Where exp_no is the experiment identifier and stage-id.txt is a"
#    echo "text file (must have .txt extension) with pairs of stage and id"
#    exit 1
#fi

##
## Setting variables
##
exp_no=$(printf "%03d" $1)
test_dir="${test_dir}-$exp_no"
mems_dir="${mems_dir}-$exp_no"
imag_dir="${imag_dir}/$exp_no"
random_dir=`basename $2 .txt`
random_dir=${imag_dir}/${random_dir}
occ_bar=$3
tol=$4
##
##
##

if [ ! -z "$occ_bar" ]; then
   mems_dir="${mems_dir}-$occ_bar"
   test_dir="${test_dir}-$occ_bar"
   random_dir="${random_dir}-$occ_bar"
fi

if [ ! -z "$tol" ]; then
   mems_dir="${mems_dir}-$tol"
   random_dir="${random_dir}-$tol"
fi
   
if [ ! -d "$test_dir" ] || [ ! -d "$mems_dir" ]; then
    echo "Directory for $test_dir or $mems_dir do not exist!"
    exit 2
fi

if [ ! -d ${random_dir}  ]; then
    mkdir -p ${random_dir}
fi

pair_fn=$2

for i in `cat $pair_fn`; do 
    IFS=',' read stage id <<< "${i}"

    echo $stage $id
    ts_dir="${test_dir}/stage_${stage}"
    ms_dir="${mems_dir}/stage_${stage}"
    dig_fn=$id

    IFS='_' read class number <<< "${dig_fn}"
    if [ $class -ge 0 ] && [ $class -le 9 ]; then
	join_imgs="${random_dir}/$(printf "%02d" $class)_${number}-join.png"	
    else
	join_imgs="${random_dir}/${dig_fn}-join.png"	
    fi

    original_img=${ts_dir}/${dig_fn}-original.png
    decoded_img=${ts_dir}/${dig_fn}.png

    memories_imgs=`find ${ms_dir} -name ${dig_fn}.png -print | sort`
    echo $memories_imgs
    convert ${original_img} ${decoded_img} $(echo $memories_imgs) -border 1 -bordercolor white -append $join_imgs     
done

join_imgs=`find ${random_dir} -type f -name '*.png' -print| sort`
final_img=${random_dir}/'all.png'
convert $(echo $join_imgs) +append ${final_img}
# mogrify -scale '1000%' ${final_img}

