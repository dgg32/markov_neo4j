import json
import sys, os
from neo4j import GraphDatabase
import operator
import copy

class import_data:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def calculate(self):

        with self.driver.session() as session:
            
            with session.begin_transaction() as tx:
                #get all hidden state names
                hidden_names_query = "MATCH (w:Hidden) RETURN DISTINCT w.name"
                hidden_names = [i["w.name"] for i in list(tx.run(hidden_names_query).data())]
                print (hidden_names)
                
                #get all observations
                get_obs_query = f"MATCH (m:Observed) RETURN m;"
                obs = {i["m"]["step"]: i["m"]["name"] for i in list(tx.run(get_obs_query).data())}
                print (obs)

                # stage 1: forward algorithm
                previous_hid_ps = {}
                for t in range(len(obs)):
                    #t = str(t)
                    current_hid_ps = {}

                    for hid in hidden_names:
                        #get emission probability
                        get_emission_p = f"MATCH (w:Hidden)-[r:emits]-(m:Observed) WHERE w.name='{hid}' AND w.step='{t}' RETURN r.p;"
                        emission_p = tx.run(get_emission_p).single()[0]

                        max_hid_p = 0
                        max_p_previous_state = ""
                        #for the fist step
                        if t == 0:
                            #get initial probability
                            get_initial_p = f"MATCH (w:Hidden {{name: '{hid}', step: '{t}'}}) RETURN w.initial_p;"
                            initial_p = tx.run(get_initial_p).single()[0]

                            print (get_initial_p, initial_p)
                            max_hid_p = emission_p * initial_p
                            
                                    
                        #for the second and later steps
                        else:
                            previous_step = t-1
                            
                            for previous_hid in hidden_names:
                                #get transition probability
                                get_transision_p = f"MATCH (w_0:Hidden)-[r:transits]-(w_1:Hidden) WHERE w_0.name='{previous_hid}' AND w_0.step='{previous_step}' AND w_1.name='{hid}' AND w_1.step='{t}' RETURN r.p;"
                                transision_p = tx.run(get_transision_p).single()[0]
                                
                                #calculate the probability
                                hid_p = emission_p * previous_hid_ps[previous_hid] * transision_p
                                #print (hid, previous_hid, "emission_p", emission_p, "previous_p[previous_weather]", previous_hid_ps[previous_hid], "transision_p", transision_p, "hid_p", hid_p)
                                if hid_p > max_hid_p:
                                    max_hid_p = hid_p
                                    max_p_previous_state = previous_hid
                            
                        #add the probability and backpointer to the node
                        add_hid_p_to_node_query = f"MATCH (w:Hidden {{name: '{hid}', step: '{t}'}}) SET w.p = {max_hid_p},  w.max_p_previous_state = '{max_p_previous_state}'; "
                        tx.run(add_hid_p_to_node_query)
                        
                        current_hid_ps[hid] = max_hid_p


                    #before move on to the next day, replace the previous weathers with the current weathers
                    previous_hid_ps = copy.deepcopy(current_hid_ps)
                
                #stage 2: backward algorithm
                #back tracing from the last node with the highest probability to find the most likely weathers
                max_p = 0
                max_hid = ""
                max_p_previous_state = ""
                for i, t in enumerate(range(len(obs) - 1, -1, -1)):
    
                    if i == 0:
                        get_name_p = f"MATCH (w:Hidden) WHERE w.step='{t}' RETURN w.name, w.p, w.max_p_previous_state;"
                        results = tx.run(get_name_p)

                        for r in results:
                            name = r[0]
                            p = r[1]
                            previous_state = r[2]

                            if p > max_p:
                                max_p = p
                                max_hid = name
                                max_p_previous_state = previous_state
                        
                        add_chosen_prop = f"MATCH (w:Hidden {{name: '{max_hid}', step: '{t}'}}) SET w :Chosen; "
                        print (add_chosen_prop)
                        tx.run(add_chosen_prop)
                    
                    else:
                        print ("max_p", max_p, "max_p_previous_state", max_p_previous_state)
                        add_chosen_prop = f"MATCH (w:Hidden {{name: '{max_p_previous_state}', step: '{t}'}}) SET w :Chosen; "
                        print (add_chosen_prop)
                        tx.run(add_chosen_prop)

                        get_previous_state = f"MATCH (w:Hidden) WHERE w.name='{max_p_previous_state}' AND w.step='{t}' RETURN w.max_p_previous_state;"
                        max_p_previous_state = tx.run(get_previous_state).single()[0]


                
ip = sys.argv[1]
password = sys.argv[2]

connection = import_data(f"bolt://{ip}:7687", "neo4j", password)

connection.calculate()

connection.close()
