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
                       {'command': ['python3',
                                    '-m',
                                    'design.extraction'],
                        'path': 'generated/extraction.json'},
                       {'command': ['python3', '-m', 'design.rules'],
                        'path': 'generated/requirements.json'}],
 'external_dependencies': [{'blocking': False,
                            'id': 'system-discharge-test',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'at_or_above_the_declared_discharge_level',
                            'review_by': '2027-03-01',
                            'statement': 'a system-level IEC 61000-4-2 '
                                         'contact discharge at the '
                                         'declared 8 kV on the '
                                         'assembled node; both fitted '
                                         'parts state device-level '
                                         'ratings only',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'oscillator-start-up-bench',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'within_the_controller_maximum_critical_transconductance',
                            'review_by': '2027-03-01',
                            'statement': 'oscillator start-up margin '
                                         'on the assembled board; '
                                         'whether a gain margin beyond '
                                         "the controller's stated "
                                         'maximum critical '
                                         'transconductance is needed '
                                         'is a vendor application-note '
                                         'question the analysis does '
                                         'not resolve',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'converter-efficiency-measurement',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'converter_efficiency_bound',
                            'review_by': '2027-03-01',
                            'statement': "the converter's efficiency "
                                         "at this board's own load is "
                                         'at least the assumed 75 '
                                         'percent',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'regulator-dropout-measurement',
                            'method': 'PHYSICAL_TEST',
                            'owner': 'bench bring-up',
                            'requirement': 'regulator_dropout_bound',
                            'review_by': '2027-03-01',
                            'statement': "the regulator's dropout at "
                                         'the logic-rail load is '
                                         'within the declared bound '
                                         'the rail claims use',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'assembly-process-confirmation',
                            'method': 'MANUFACTURING_CHECK',
                            'owner': 'fabrication order review',
                            'review_by': '2027-03-01',
                            'statement': 'the assembler builds this '
                                         'board to the declared '
                                         'process: one lead-free '
                                         'reflow pass peaking no '
                                         'higher than 245 C, top side '
                                         'only, no-clean, with the '
                                         'through-hole connectors '
                                         'hand-soldered after reflow',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'part-supply-at-order',
                            'method': 'MANUFACTURING_CHECK',
                            'owner': 'fabrication order review',
                            'review_by': '2027-03-01',
                            'statement': 'every fitted part is still '
                                         'supplied at order time; the '
                                         'lifecycle domain is declined '
                                         'because no source this board '
                                         'freezes states a lifecycle, '
                                         'so the question is answered '
                                         'by the order itself',
                            'status': 'open'},
                           {'blocking': False,
                            'id': 'jlcpcb-assembly-preview',
                            'method': 'MANUFACTURING_CHECK',
                            'owner': 'fabrication order review',
                            'review_by': '2027-03-01',
                            'statement': "JLCPCB's own assembly "
                                         'preview shows every part at '
                                         'its intended position and '
                                         'rotation',
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

REQUIRED_DOMAINS = ['claims', 'requirements', 'simulation',
                    'external_dependencies', 'thermal',
                    'reference_continuity', 'assembly_process']

DECLINED_DOMAINS = [{'domain': 'lifecycle',
  'reason': "a lifecycle status is a person's reading of a statement about supply, and neither source this board can freeze makes one: the committed catalogue snapshot carries stock, price and library type, and the per-part endpoint the toolkit freezes adds an on-sale flag. Every entry a snapshot could hold today would therefore be `unestablished`, which is not a state a release stands on, and reading a stock count as `active` is the false confidence the snapshot exists to prevent. The availability half is already judged from that stock - the build quantity is checked against it in design/cost.py - and the lifecycle half is carried as the open part-supply-at-order dependency the fabrication order review owns"},
 {'domain': 'timing',
  'reason': 'no timing interfaces are declared; the bus is judged by '
            'rate qualification and oscillator budget, not by a '
            'per-net timing budget'},
 {'domain': 'device_parameters',
  'reason': 'device figures live in components/parameters.json with '
            'per-figure document citations; the typical-only figures '
            'this board leans on (enable threshold, capacitance '
            'mismatch) are recorded as claim assumptions'},
 {'domain': 'orientation',
  'reason': 'no part on this board needs a rotation correction; the '
            'CPL ships library angles and the fabrication order review '
            'checks the preview'},
 {'domain': 'current_capacity',
  'reason': "the field supply carries a full amp to the connector and its two layer changes are exactly the conductors a capacity check would decide, so this is a real question for this board and not an absent one. It stays declined for one reason: a capacity basis is an empirical curve fit with a standard, an edition and a fitted window behind it, and none has been sourced. Inventing coefficients to get an answer would be worse than not having one"},
 {'domain': 'power_integrity',
  'reason': "the rails are judged as claims against the regulator's stated output; no rail is poured as a plane whose drop a solve would decide"},
 {'domain': 'differential_pairs',
  'reason': "this board DOES route a CAN differential pair, and its impedance is not yet judged by SI.PAIR_IMPEDANCE: the pair is held by the bus standard's own termination requirement and by the board's claims, and no cross-section has been declared for the coupled model. Declaring it is the next revision's work and is named here rather than left silent. The fabricator publishes a stackup for four and six layers and offers controlled impedance from four layers up, so for this two-layer board there is no published cross-section to declare one from"}]

EXTRA_SOURCE_CLOSURE = ['evidence/datasheets/*', 'generated/requirements.json']


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
