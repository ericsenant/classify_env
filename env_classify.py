import pandas as pd
import json
import numpy as np
import math
import csv
import sys
import matplotlib.pyplot as plt
from   pandas.io.json import json_normalize

print ("env_classify Input file : {}". format ( sys . argv [1]))
filename = sys.argv[1]
if len(sys.argv)>2:
    obs_rate = int(sys.argv[2])
else:
    obs_rate = int(2)

average_window       = 300
highway_threshold    = 68
denseurban_threshold = 45

table        = []
init         = []
stats_azel   = [0,0,0,0]
previous_tow = -1
iconSize     = 0.6
iconColor    = []
envMetric    = float("NaN")
envMetric_MA = float("NaN")
count_lines  = 0
n_obs        = 0
count_code_phase_valid_L1       = 0

kmlOutput = open (filename + ".kml","w")
kmlOutput.write('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">\n');
kmlOutput.write('<Document><Folder><name>GNSS</name>\n');

# the json script in input should be generated in lines like :
#   cat my_log.sbp | sbp2json | jq -c "select(.msg_type==74 or .msg_type==151)" > 74_in_lines.json
with open (filename,"r") as f:
    table  = [json.loads(line) for line in f]
    header = ['tow','cn0_L1_median','cn0_L1_std','envMetric','envMetric_MA', 'total_G','count_code_phase_valid_L1','count_carrier_phase_valid_L1','count_half_cycle_phase_valid_L1', 'count_doppler_valid_L1']
    output = pd.DataFrame({'tow':[],'cn0_L1_median':[],'cn0_L1_std':[]})
    output.to_csv(filename + '_output.csv')

    csv_azel   = open(filename + '_azel.csv', 'w', newline='')
    azel_writer = csv.writer(csv_azel, delimiter=',')

    for json_data in table:
        # obs processing
        if json_data['msg_type'] == 74:

            if (json_data['header']['t']['tow']%1000 < 10 or json_data['header']['t']['tow']%1000 > 990): # 1Hz processing

                page_counter = json_data['header']['n_obs']-(json_data['header']['n_obs']>> 4)*16
                nb_obs_pages = json_data['header']['n_obs']>> 4

                df1 = pd.DataFrame(json_normalize(json_data['obs'], max_level=1))

                if page_counter == 0: # new sequence of MSG74 pages

                    previous_tow                    = json_data['header']['t']['tow']
                    count_half_cycle_phase_valid_L1 = 0
                    count_carrier_phase_valid_L1    = 0
                    count_code_phase_valid_L1       = 0
                    count_doppler_valid_L1          = 0
                    median_cn0_L1                   = 0
                    stdev_cn0_L1                    = 0
                    total_G                         = 0
                    n_obs                           = json_data['header']['n_obs'] >> 4
                    old_df1                         = df1.copy()

                else:
                    df2             = pd.concat([old_df1,df1], ignore_index=True, sort=True) # concatenate several obs messages from the same epoch
                    # df2             = df2[df2['sid.code'].isin([0])] # could reduce memory usage if we limit the dataframe ton L1CA only
                    old_df1         = df2.copy()

                # decoding the current obs frame
                if n_obs > 0:

                    for item in json_data['obs']:
                        df=pd.DataFrame(item)
                        df.style.hide_index()

                        # Computation for L1CA
                        if int(df['sid']['code']) in [0]:
                            total_G +=1
                            if ((df['flags'][0])%2):
                                count_code_phase_valid_L1 += 1
                            if ((df['flags'][0]>>1)%2):
                                count_carrier_phase_valid_L1 += 1
                            if ((df['flags'][0]>>2)%2):
                                count_half_cycle_phase_valid_L1 += 1
                            if ((df['flags'][0]>>3)%2):
                                count_doppler_valid_L1 += 1

                    if page_counter == nb_obs_pages - 1:
                        if count_code_phase_valid_L1 != 0:
                            envMetric = count_half_cycle_phase_valid_L1/count_code_phase_valid_L1*100
                        else:
                            envMetric    = float("NaN") # we need to avoid division by 0 in case of GNSS-denied
                            envMetric_MA = float("NaN")
                        if count_lines > 0:
                            list_epochs  = list(range(int(max(0,count_lines-average_window)),count_lines))
                            envMetric_MA = output.iloc[list_epochs,6].mean(axis=0)

                        new_record  = pd.DataFrame([[json_data['header']['t']['tow']/1000, median_cn0_L1, stdev_cn0_L1, envMetric, envMetric_MA, total_G, count_code_phase_valid_L1, count_carrier_phase_valid_L1,count_half_cycle_phase_valid_L1, count_doppler_valid_L1]], columns=header)
                        output      = output.append(new_record, ignore_index=True, sort=True)
                        # new_record.style.hide_index()
                        new_record.to_csv(filename + '_output.csv', columns=header, mode='a', header=False, index=False)
                        count_lines += 1
                else:
                    envMetric   = float("NaN")
                    envMetric_MA= float("NaN")
                    if json_data['header']['t']['tow'] != 0:
                        new_record  = pd.DataFrame([[json_data['header']['t']['tow']/1000,"NaN","NaN","NaN",0,0,0,0,0]], columns=header)
                        output      = output.append(new_record, ignore_index=True,sort=True)

        # elif json_data['msg_type'] == 151:
        #     df_151=pd.DataFrame(json_data['azel'])
        #     df_151.style.hide_index()
        #     df_151["az"] = np.arctan(abs(np.tan(df_151["az"]*2/180*math.pi)))/math.pi*180
        #     df_151.loc[df_151["el"]<0, ['az']] = np.nan # ublox init error handling
        #     df_151.loc[df_151["el"]<0, ['el']] = np.nan # ublox init error handling
        #     # print(df_151)
        #     stats_azel= [df_151["az"].median(), df_151["az"].std(), df_151["el"].median(), df_151["el"].std()]
        #     # print(stats_azel)
        #     azel_writer.writerow([previous_tow/1000,stats_azel[0],stats_azel[1],stats_azel[2],stats_azel[3]])

        elif json_data['msg_type'] == 522:

            if (json_data['tow']%1000 < 10 or json_data['tow']%1000 > 990): # KML plotting at 1Hz

                if n_obs >0 and json_data['tow']>0:
                    # KML coloring: highway: green, urban: orange, denseUrban:red, GNSS-denied: black
                    if (envMetric_MA < denseurban_threshold): # Dense Urban
                        iconColor = 'cc0000ff'  # Red
                    else:
                        if (envMetric_MA > highway_threshold): # highway
                            iconColor = 'cc00ff00'  # Green
                        else: # suburban / foliage / urban
                            iconColor = 'cc0073ff'  # Orange
                    if count_code_phase_valid_L1 < 4: #GNSS-denied
                        iconColor = 'cc000000'  # Black
                else:
                    iconColor = 'cc000000'  # Black

                kmlOutput.write("<Placemark><Style><IconStyle><scale>{0}</scale><color>{1}</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>\n".format(iconSize, iconColor));
                kmlOutput.write("<Point><coordinates>{0:3.6f},{1:3.6f},{2:4.2f}</coordinates></Point>\n".format(json_data['lon'],json_data['lat'],json_data['height']))
                kmlOutput.write('<description><![CDATA[<table width="180"><tr><td><p style="line-height:18px;"><font face="Arial"><b>TOW:</b>{0:6.2f} s</font></p></td></tr></table>]]></description></Placemark>\n'.format(json_data['tow']/1000))

    # Plotting
    output.to_csv(filename + '_output_env_metric.csv', columns=header)

    # Ending KML
    kmlOutput.write("</Folder></Document></kml>\n");
    kmlOutput.close()

    # Environment metric
    bx=output.plot(x='tow', y=['envMetric','envMetric_MA'])
    bx.set_xlabel('TOW [s]')
    bx.set_ylabel('Count')
    bx.set_title('Environment classification metric')
    bx.grid(color='0.8',axis='both')
    # bx.savefig(filename + 'HCAR-ratio_CN0.png')

    plt.savefig(filename + '.png', format="png")
    # plt.show()
