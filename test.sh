#!/bin/bash

OUTPUT_FILE="steadyState.csv"

solomon_instances=(
    "Solomon/10/C101" "Solomon/10/C201" "Solomon/10/R101" "Solomon/10/RC101"
    "Solomon/15/C101" "Solomon/15/C201" "Solomon/15/R101" "Solomon/15/RC101"
    "Solomon/20/C101" "Solomon/20/C201" "Solomon/20/R101" "Solomon/20/RC101"
    "Solomon/25/C101" "Solomon/25/C201" "Solomon/25/R101" "Solomon/25/RC101"
    "Solomon/30/C101" "Solomon/30/C201" "Solomon/30/R101" "Solomon/30/RC101"
    "Solomon/35/C101" "Solomon/35/C201" "Solomon/35/R101" "Solomon/35/RC101"
    "Solomon/40/C101" "Solomon/40/C201" "Solomon/40/R101" "Solomon/40/RC101"
    "Solomon/45/C101" "Solomon/45/C201" "Solomon/45/R101" "Solomon/45/RC101"
    "Solomon/50/C101" "Solomon/50/C201" "Solomon/50/R101" "Solomon/50/RC101"
    "Solomon/100/C101" "Solomon/100/C201" "Solomon/100/R101" "Solomon/100/RC101"
)
tsplib_instances=(
    "TSPLIB/eil51" "TSPLIB/berlin52" "TSPLIB/st70" "TSPLIB/eil76"
    "TSPLIB/pr76" "TSPLIB/rat99" "TSPLIB/kroA100" "TSPLIB/kroB100"
    "TSPLIB/kroC100" "TSPLIB/kroD100" "TSPLIB/kroE100" "TSPLIB/rd100"
    "TSPLIB/eil101" "TSPLIB/lin105" "TSPLIB/pr107" "TSPLIB/pr124"
    "TSPLIB/bier127" "TSPLIB/ch130" "TSPLIB/pr136" "TSPLIB/pr144"
    "TSPLIB/ch150" "TSPLIB/kroA150" "TSPLIB/kroB150" "TSPLIB/pr152"
    "TSPLIB/u159" "TSPLIB/rat195" "TSPLIB/d198" "TSPLIB/kroA200"
    "TSPLIB/kroB200" "TSPLIB/ts225" "TSPLIB/tsp225" "TSPLIB/pr226"
    "TSPLIB/gil262" "TSPLIB/pr264" "TSPLIB/a280" "TSPLIB/pr299"
    "TSPLIB/lin318" "TSPLIB/rd400" "TSPLIB/fl417" "TSPLIB/pr439"
    "TSPLIB/pcb442" "TSPLIB/d493"
)
atsplib_instances=(
    "aTSPLIB/ftv33" "aTSPLIB/ft53" "aTSPLIB/ftv70" "aTSPLIB/kro124p" "aTSPLIB/rbg403"
)

all_instances=(
    "${solomon_instances[@]}"
    "${tsplib_instances[@]}"
    "${atsplib_instances[@]}"
)

betas=("0.5" "1" "1.5" "2" "2.5" "3")

echo "DATASET,INSTANCE,BETA,AVG_EXEC_TIME,AVG_SOL_TIME,AVG_OBJ,BEST_OBJ" > $OUTPUT_FILE

for instance in "${all_instances[@]}"; do
    DATASET=$(echo "$instance" | awk -F'/' '{print $1}')
    INSTANCE=$(echo "$instance" | awk -F'/' '{print $2"/"$3}')

    for beta in "${betas[@]}"; do
        total_exec_time=0
        total_sol_time=0
        total_obj=0
        best_obj=0
        
        for RUN in $(seq 1 10); do
            FILE_PATH="instances/${instance}_${beta}.dat"
            RESULT=$(./build/TSPrd "$FILE_PATH" -o output.txt)

            EXEC_TIME=$(echo "$RESULT" | grep "EXEC_TIME" | awk '{print $2}')
            SOL_TIME=$(echo "$RESULT" | grep "SOL_TIME" | awk '{print $2}')
            OBJ=$(echo "$RESULT" | grep "OBJ" | awk '{print $2}')
            SEED=$(echo "$RESULT" | grep "SEED" | awk '{print $2}')

            (( total_obj += OBJ ))
            (( total_sol_time += SOL_TIME ))
            (( total_exec_time += EXEC_TIME ))

            if [[ "$best_obj" -eq 0 || $(echo "$OBJ < $best_obj" | bc -l) -eq 1 ]]; then
                best_obj=$OBJ
            fi
            
            echo "Completed run $RUN for $DATASET/$INSTANCE with beta $beta"
        done
        avg_obj=$(echo "scale=2; $total_obj / 5" | bc)
        avg_exec_time=$(echo "scale=2; $total_exec_time / 5" | bc)
        avg_sol_time=$(echo "scale=2; $total_sol_time / 5" | bc)
        echo "$DATASET,$INSTANCE,$beta,$avg_exec_time,$avg_sol_time,$avg_obj,$best_obj" >> $OUTPUT_FILE
    done
done

echo "All tests completed, results saved to $OUTPUT_FILE"

