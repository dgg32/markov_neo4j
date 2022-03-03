import json
import sys, os
from neo4j import GraphDatabase

examples = {
    "1": {
        "observed_states": ["normal", "cold", "dizzy"],
        "emission_p": {'Healthy': {"normal": 0.5, "cold": 0.4, "dizzy": 0.1}, 'Fever': {"normal": 0.1, "cold": 0.3, "dizzy": 0.6}},
        "transition_p": {'Healthy': {"Healthy": 0.7, "Fever": 0.3}, 'Fever': {"Healthy": 0.4, "Fever": 0.6}},
        "initial_p": {"Healthy": 0.6, "Fever": 0.4}
    },
    "2": {
        "observed_states": ["Happy", "Happy", "Sad", "Sad", "Sad", "Happy"],
        "emission_p": {'Rainy': {"Happy": 0.4, "Sad": 0.6}, 'Sunny': {"Happy": 0.8, "Sad": 0.2}},
        "transition_p": {'Rainy': {"Sunny": 0.4, "Rainy": 0.6}, 'Sunny': {"Sunny": 0.8, "Rainy": 0.2}},
        "initial_p": {"Sunny": 2/3, "Rainy": 1/3}
    },
    "3": {
        "observed_states": ["G", "G", "C", "A", "C", "T", "G", "A", "A"],
        "emission_p": {'H': {"A": 0.2, "C": 0.3, "G": 0.3, "T": 0.2}, 'L': {"A": 0.3, "C": 0.2, "G": 0.2, "T": 0.3}},
        "transition_p": {'H': {"H": 0.5, "L": 0.5}, 'L': {"H": 0.4, "L": 0.6}},
        "initial_p": {"H": 0.5, "L": 0.5}
    }
}


class import_data:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_nodes_connections(self, example):
        if example in examples:
            
            observed_states = examples[example]["observed_states"]
            emission_p = examples[example]["emission_p"]
            transition_p = examples[example]["transition_p"]
            initial_p = examples[example]["initial_p"]
            hidden_states =  list(initial_p.keys())

            with self.driver.session() as session:
                with session.begin_transaction() as tx:

                    #create observation nodes
                    for step, ob in enumerate(observed_states):

                        create_ob_query = f"CREATE (w:Observed {{name: '{ob}', step: '{step}'}}); "
                        tx.run(create_ob_query)

                        for hid in hidden_states:
                            #create hidden states
                            create_hid_query = f"CREATE (w:Hidden {{name: '{hid}', step: '{step}'}}); "
                            tx.run(create_hid_query)

                            #create emissions
                            emission_query = f"MATCH (w:Hidden), (m:Observed) WHERE w.name = '{hid}' AND w.step='{step}' AND m.name = '{ob}' AND m.step = '{step}' CREATE (w)-[r:emits {{name: '{hid}-emits-{ob}', p: {emission_p[hid][ob]}}}]->(m)"
                            tx.run(emission_query)

                        
                            if step > 0:
                                #create transitions
                                for hid_2 in hidden_states:
                                    hid_hid_connect_query = f"MATCH (w:Hidden), (w2:Hidden) WHERE w.name = '{hid_2}' AND w.step='{step-1}' AND w2.name = '{hid}' AND w2.step = '{step}' CREATE (w)-[r:transmits {{name: '{hid_2}-transmits-{hid}', p: {transition_p[hid_2][hid]}}}]->(w2)"
                                    tx.run(hid_hid_connect_query)
                            else:
                                #initial p
                                create_init_query = f"MATCH (w:Hidden {{name: '{hid}', step: '{step}'}}) SET w.initial_p = {initial_p[hid]}; "
                                tx.run(create_init_query)

                    tx.commit()

                
ip = sys.argv[1]
password = sys.argv[2]
example = sys.argv[3]

connection = import_data(f"bolt://{ip}:7687", "neo4j", password)

connection.add_nodes_connections(example)

connection.close()
