import argparse

from pandas.core.groupby import DataFrameGroupBy

from tables_saving import *
from tsprd_data import *


def main():
    parser = argparse.ArgumentParser(description="Generate table from the executor instance execution results folder.")
    parser.add_argument("results_folder", action="store", type=str,
                        help="Folder with the TSPrd instance execution results.")
    args = parser.parse_args()

    gen_tables(args.results_folder)
    print("Finished!")


def gen_tables(results_folder: str):
    df = read_execution_data(results_folder)  # read the results of the executions
    df_agg = aggregate_data(df)  # group the 10 executions and calculate the relevant data (means, sums)
    solomon_opt, solomon_mixed, solomon50, solomon100, tsplib, atsplib = split_instance_sets(df_agg)

    gen_solomon_tables(solomon_opt, solomon_mixed, solomon50, solomon100)
    gen_tsplib_tables(tsplib)
    gen_atsplib_table(atsplib)
    gen_opt_summary_table(solomon_opt)
    gen_nopt_summary_table(solomon50, solomon100, tsplib, atsplib)


def gen_solomon_tables(solomon_opt: pd.DataFrame, solomon_mixed: pd.DataFrame, solomon50: pd.DataFrame, solomon100: pd.DataFrame):
    for n, df in chain(solomon_opt.groupby(level=0), solomon_mixed.groupby(level=0), solomon50.groupby(level=0), solomon100.groupby(level=0)):  # iterate a dataframe for each `n`
        for check in ["ref_obj", "ref_time", "ref_gap", "best_known"]:
            if check in df and df[check].isna().all():
                df.drop(columns=check, inplace=True)
        df = df.droplevel(0)
        save_table(f"solomon{n}", f"Results for Solomon instances with n = {n}", df)


def gen_tsplib_tables(tsplib: pd.DataFrame):
    tsplib = tsplib.sort_index(level=["beta", "n"]).droplevel("n")

    tsplib_betas, tsplib_dfs = zip(*tuple(tsplib.groupby(level="beta")))
    for i in range(0, 6, 2):
        beta1, beta2 = tsplib_betas[i:i + 2]
        tsplib_two = pd.concat([tsplib_dfs[i].droplevel("beta"), tsplib_dfs[i + 1].droplevel("beta")],
                               axis="columns", keys=[beta1, beta2])
        save_table(f"tsplib_{beta1}_{beta2}", f"Results for TSPLIB instances with $\\beta \\in {{{beta1}, {beta2}}}$", tsplib_two,
                   add_options="\\setlength{\\tabcolsep}{3pt} \\tiny")


def gen_atsplib_table(atsplib: pd.DataFrame):
    atsplib = atsplib.sort_index(level=["beta", "n"]).droplevel("n")
    save_table(f"atsplib", "Results for aTSPLIB instances", atsplib)


def gen_opt_summary_table(solomon_opt: pd.DataFrame):
    sol_opt = solomon_opt.query("n <= 20").groupby(["n", "beta"]) \
        .agg(n_inst=("exec_time", "count"), ref_gap=("ref_gap", "mean"), ref_time=("ref_time", "mean"), gap_best=("gap_best", "mean"),
             gap_avg=("gap_avg", "mean"), exec_time=("exec_time", "mean"), sol_time=("sol_time", "mean"))
    sol_opt["ref_time"] = sol_opt["ref_time"].apply(lambda x: "-" if pd.isna(x) else int(x))

    # count how many each equal the optimal result
    sol_opt.insert(sol_opt.columns.get_loc("ref_gap"), "n_ref_opt",
                   solomon_opt.query("ref_obj == opt", engine="python").groupby(sol_opt.index.names).size())
    sol_opt.insert(sol_opt.columns.get_loc("gap_best"), "n_opt_best",
                   solomon_opt.query("best_obj == opt", engine="python").groupby(sol_opt.index.names).size())
    sol_opt.insert(sol_opt.columns.get_loc("gap_avg"), "n_opt_avg",
                   solomon_opt.query("avg_obj == opt", engine="python").groupby(sol_opt.index.names).size())

    save_table("summary_opt", "Comparison of aggregated results for instances with known optimal",
               sol_opt, add_options="\\fontsize{9pt}{11pt}\\selectfont")


def gen_nopt_summary_table(solomon50: pd.DataFrame, solomon100: pd.DataFrame, tsplib: pd.DataFrame, atsplib: pd.DataFrame):
    sol50_agg = gen_solomon_nopt_summary(solomon50.drop(columns=["opt"]))
    sol100_agg = gen_solomon_nopt_summary(solomon100)
    tsplib_agg = gen_tsplib_summary(tsplib)
    atsplib_agg = gen_atsplib_summary(atsplib)

    summary_nopt = pd.concat([sol50_agg, sol100_agg, tsplib_agg, atsplib_agg], keys=["Solomon", "TSPLIB", "aTSPLIB"])
    summary_nopt[["n_ref_sb_best", "n_ref_sb_avg", "n_sb_best", "n_sb_avg"]] = \
        summary_nopt[["n_ref_sb_best", "n_ref_sb_avg", "n_sb_best", "n_sb_avg"]].fillna(0).astype(int)
    save_table("summary_nopt", "Comparison of aggregated results for the instances in which the optimal solution is unknown", summary_nopt,
               add_options="\\fontsize{8pt}{10pt}\\selectfont \\setlength{\\tabcolsep}{2.5pt}")


def gen_solomon_nopt_summary(solomon_nopt: pd.DataFrame):
    sol_grouped = solomon_nopt.groupby(["n", "beta"])
    sol_agg = nopt_summary_agg(sol_grouped)
    return sol_agg


def gen_tsplib_summary(tsplib: pd.DataFrame):
    tsplib_grouped = tsplib.groupby([pd.cut(tsplib.index.get_level_values("n"), bins=[49, 100, 150, 250, 500]), "beta"])
    tsplib_agg = nopt_summary_agg(tsplib_grouped)
    return tsplib_agg


def gen_atsplib_summary(atsplib: pd.DataFrame):
    atsplib_grouped = atsplib.groupby([pd.cut(atsplib.index.get_level_values("n"), bins=[32, 403]), "beta"])
    atsplib_agg = nopt_summary_agg(atsplib_grouped)
    return atsplib_agg


def nopt_summary_agg(df_grouped: DataFrameGroupBy):
    df_agg = df_grouped.agg(n_inst=("ref_obj", "count"), gap_best=("gap_best", "mean"), gap_avg=("gap_avg", "mean"), exec_time=("exec_time", "mean"),
                            sol_time=("sol_time", "mean"))

    ref_pos = df_agg.columns.get_loc("n_inst") + 1  # position to insert next few columns
    df_agg.insert(ref_pos, "n_ref_sb_best", df_grouped.apply(lambda d: d[d["ref_obj"] < d["best_obj"]].shape[0]))
    df_agg.insert(ref_pos + 1, "n_ref_sb_avg", df_grouped.apply(lambda d: d[d["ref_obj"] < d["avg_obj"]].shape[0]))
    df_agg.insert(df_agg.columns.get_loc("gap_best"), "n_sb_best",
                  df_grouped.apply(lambda d: d[d["best_obj"] < d["ref_obj"]].shape[0]))
    df_agg.insert(df_agg.columns.get_loc("gap_avg"), "n_sb_avg",
                  df_grouped.apply(lambda d: d[d["avg_obj"] < d["ref_obj"]].shape[0]))
    ref_time_column = df_grouped["ref_time"].mean().astype(int) if "ref_time" in df_grouped.describe() else "-"
    df_agg.insert(df_agg.columns.get_loc("n_ref_sb_avg") + 1, "ref_time", ref_time_column)
    return df_agg


if __name__ == "__main__":
    main()
