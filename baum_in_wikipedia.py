import json
import sys, os
from neo4j import GraphDatabase
import itertools
import copy
import operator

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

                hidden_state_combi = list(itertools.product(hidden_names, repeat=2))
                print ("hidden_state_combi", hidden_state_combi)
                
                #get all observations
                get_obs_query = f"MATCH (m:Observed) RETURN m;"
                obs = {i["m"]["step"]: i["m"]["name"] for i in list(tx.run(get_obs_query).data())}
                print (obs)

                o_pairs = {}

                pairs = tuple((obs[str(i)], obs[str(i+1)]) for i in range(len(obs)-1))
                for pair in pairs:
                    if pair not in o_pairs:
                        o_pairs[pair] = 0
                    o_pairs[pair] += 1

                get_initial_p = f"MATCH (h:Hidden {{step: '0'}}) RETURN h;"
                initial_p = {i["h"]["name"]: i["h"]["initial_p"] for i in list(tx.run(get_initial_p).data())}
                print (initial_p)

                #get_transition_p = f"MATCH (h:Hidden {{step: '0'}}) -[t:transits]-> (h2:Hidden {{step: '1'}}) RETURN t;"
                get_transition_p = f"MATCH p=(h1:Hidden {{step: '0'}})-[t:transits]->(h2:Hidden) RETURN h1, t, h2;"
                #print (get_transition_p)
                results = tx.run(get_transition_p)
                transition_p = {}
                #print ("results", results)
                for result in results:
                    
                    h1 = result.get("h1").get("name")
                    h2 = result.get("h2").get("name")
                    p = result.get("t").get("p")
                    if h1 not in transition_p:
                        transition_p[h1] = {}
                    transition_p[h1][h2] = p
                #transition_p = {i["t"]["name"].split("-transmits-")[0]: i["t"]["initial_p"].split("-transmits-")[1] for i in list(tx.run(get_transition_p).data())}
                print (transition_p)
                
                emission_p = {}
                for o in set(obs.values()):
                    for h in hidden_names:
                        get_emission_p = f"MATCH p=(h1:Hidden {{name: '{h}'}})-[t:emits]->(o:Observed {{name: '{o}'}}) RETURN t;"
                        results = tx.run(get_emission_p)
                        if h not in emission_p:
                            emission_p[h] = {}
                        
                        for result in results:
                            emission_p[h][o] = result.get("t").get("p")
                        #print (get_emission_p)
                print (emission_p)
                

                ######### update transtion_p
                pseudo_p = {}
                pseudo_transition_p = {}
                for pair in o_pairs:
                    for hidden_state_c in hidden_state_combi:                        

                        p = initial_p[hidden_state_c[0]] * transition_p[hidden_state_c[0]][hidden_state_c[1]] * emission_p[hidden_state_c[0]][pair[0]] * emission_p[hidden_state_c[1]][pair[1]]

                        print (pair, hidden_state_c, p)

                        if pair not in pseudo_p:
                            pseudo_p[pair] = {}
                        if hidden_state_c not in pseudo_p[pair]:
                            pseudo_p[pair][hidden_state_c] = p

                        
                        if hidden_state_c not in pseudo_transition_p:
                            pseudo_transition_p[hidden_state_c] = 0
                        pseudo_transition_p[hidden_state_c] += p * o_pairs[pair]
                print ("pseudo_p", pseudo_p)

                print (pseudo_transition_p)

                max_pseudo_p_sum = 0
                max_pseudo_p = {}
                for pair in pseudo_p:
                    
                    hidden_state_c, max_p = max(pseudo_p[pair].items(), key=operator.itemgetter(1))
                    print ("max_p", pair, hidden_state_c, max_p)

                    max_pseudo_p[pair] = max_p

                    max_pseudo_p_sum += max_p * o_pairs[pair]

                print ("max_pseudo_p_sum", max_pseudo_p_sum)

                hid_sum = {}
                for pseudo_transition in pseudo_transition_p:
                    pseudo_transition_p[pseudo_transition] /= max_pseudo_p_sum

                    if pseudo_transition[0] not in hid_sum:
                        hid_sum[pseudo_transition[0]] = 0
                    hid_sum[pseudo_transition[0]] += pseudo_transition_p[pseudo_transition]
                
                print (pseudo_transition_p)
                print (hid_sum)

                for pseudo_transition in pseudo_transition_p:
                    pseudo_transition_p[pseudo_transition] /= hid_sum[pseudo_transition[0]]

                print (pseudo_transition_p)


                ######### update emission_p
                pseudo_emission_p = {}

                for o in set(obs.values()):
                    if o not in pseudo_emission_p:
                        pseudo_emission_p[o] = {}
                    for hid in hidden_names:
                        if hid not in pseudo_emission_p[o]:
                            pseudo_emission_p[o][hid] = {}

                        for ob in pseudo_p:
                            if o in ob:
                                pseudo_emission_p[o][hid][ob] = 0
                                for transition in pseudo_p[ob]:
                                    Go = True
                                    for o_temp, h_temp in zip(ob, transition):
                                        if o_temp == o and h_temp != hid:
                                            Go = False
                                    if Go == True:
                                        print (ob, transition, o, hid)
                                        print (f"for {o} from {hid}: {ob} vs {transition}: {pseudo_p[ob][transition]}")
                                        if pseudo_p[ob][transition] > pseudo_emission_p[o][hid][ob]:
                                            pseudo_emission_p[o][hid][ob] = pseudo_p[ob][transition]
                                            
                            
                        
                print (pseudo_emission_p)


                

ip = sys.argv[1]
password = sys.argv[2]

connection = import_data(f"bolt://{ip}:7687", "neo4j", password)

connection.calculate()

connection.close()
