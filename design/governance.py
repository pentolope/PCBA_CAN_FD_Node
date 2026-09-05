"""Evidence governance this board declares, as data.

The manifest generator merges these blocks into its own document, so the
committed manifest and the generated one agree by construction - the
same discipline every other derived document lives under. Policy content
lives here; the merge logic is `merged` below.
"""

TOP = {'claims': {'approximate': {'default': 'permitted-with-label'},
            'document': 'generated/requirements.json',
            'unsupported': {'default': 'blocking', 'permitted': []}},
 'derived_documents': [{'command': ['python3',
                                    '-m',
                                    'design.requirements'],
                        'path': 'constraints/requirements.json'},
                       {'command': ['python3', '-m', 'design.extraction'],
                        'path': 'generated/extraction.json'},
                       {'command': ['python3', '-m', 'design.rules'],
                        'path': 'generated/requirements.json'}],
 'external_dependencies': [{'blocking': False,
                            'id': 'system-discharge-test',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'at_or_above_the_declared_discharge_level',
                            'statement': 'a system-level IEC 61000-4-2 '
                                         'contact discharge at the '
                                         'declared 8 kV on the assembled '
                                         'node; both fitted parts state '
                                         'device-level ratings only',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'oscillator-start-up-bench',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'within_the_controller_maximum_critical_transconductance',
                            'statement': 'oscillator start-up margin on '
                                         'the assembled board; whether a '
                                         'gain margin beyond the '
                                         "controller's stated maximum "
                                         'critical transconductance is '
                                         'needed is a vendor '
                                         'application-note question the '
                                         'analysis does not resolve',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'converter-efficiency-measurement',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'converter_efficiency_bound',
                            'statement': "the converter's efficiency at "
                                         "this board's own load is at "
                                         'least the assumed 75 percent',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'regulator-dropout-measurement',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'regulator_dropout_bound',
                            'statement': "the regulator's dropout at the "
                                         'logic-rail load is within the '
                                         'declared bound the rail claims '
                                         'use',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'jlcpcb-assembly-preview',
                            'method': 'MANUFACTURING_CHECK',
                            'owner': 'fabrication order review',
                            'statement': "JLCPCB's own assembly preview "
                                         'shows every part at its '
                                         'intended position and rotation',
                            'status': 'open'}],
 'provenance': {'evidence_index': 'evidence/index.json'},
 'requirements': {'minimum_methods': {'fault_tolerance': ['ANALYTIC'],
                                      'safe_state': ['ANALYTIC',
                                                     'STATIC']},
                  'register': 'constraints/requirements.json'}}

EXTRA_MANDATORY_GATES = ['CLAIM.MATRIX',
 'CLAIM.POLICY',
 'EXT.DEPENDENCIES',
 'PROV.DERIVED_DOCUMENTS',
 'PROV.EVIDENCE_INTEGRITY',
 'REQ.CLAIM_JOIN',
 'REQ.REGISTER']

EXTRA_REQUIRED_EVIDENCE = ['constraints/requirements.json', 'generated/extraction.json']

REQUIRED_DOMAINS = ['claims', 'requirements', 'simulation', 'external_dependencies']

DECLINED_DOMAINS = [{'domain': 'timing',
  'reason': 'no timing interfaces are declared; the bus is judged by '
            'rate qualification and oscillator budget, not by a per-net '
            'timing budget'},
 {'domain': 'device_parameters',
  'reason': 'device figures live in components/parameters.json with '
            'per-figure document citations; the typical-only figures '
            'this board leans on (enable threshold, capacitance '
            'mismatch) are recorded as claim assumptions'},
 {'domain': 'orientation',
  'reason': 'no part on this board needs a rotation correction; the CPL '
            'ships library angles and the fabrication order review '
            'checks the preview'}]

EXTRA_SOURCE_CLOSURE = ['evidence/datasheets/*']



def merged(document):
    import copy

    doc = copy.deepcopy(document)
    doc.update(copy.deepcopy(TOP))
    profile = doc["release_profile"]
    profile["mandatory_gates"] = sorted(
        set(profile["mandatory_gates"]) | set(EXTRA_MANDATORY_GATES))
    profile["required_evidence"] = sorted(
        set(profile.get("required_evidence", []))
        | set(EXTRA_REQUIRED_EVIDENCE))
    profile["required_domains"] = list(REQUIRED_DOMAINS)
    profile["declined_domains"] = copy.deepcopy(DECLINED_DOMAINS)
    closure = doc["reports"]["source_closure"]
    for pattern in EXTRA_SOURCE_CLOSURE:
        if pattern not in closure:
            closure.append(pattern)
    return doc
