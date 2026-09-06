"""What the design source claims about itself, checked.

The board is generated, so the files in the tree are only as good as the
source that wrote them and the source is only as good as what can be shown
about it. These are the showings: that the netlist is internally consistent,
that the committed files are the ones the source produces, that every
document a parameter leans on is frozen and intact, that every requirement
resolves, that every scenario runs, and that the schematic passes the checker
that does not care what the source intended.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from design import (build, cost, evidence, extraction, ksym,  # noqa: E402
                    layout, libraries, manifest, netlist, physical, rules,
                    simulation, thermal)

TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa.sim import model_registry, ngspice  # noqa: E402
from pcbqa.sim import scenario as sim_scenario  # noqa: E402


class DesignSource(unittest.TestCase):
    def test_no_board_code_calls_saveboard_directly(self):
        """Every board write goes through `pcbqa.board.save`.

        `pcbnew.SaveBoard` rewrites - or invents - the sibling project
        documents beside whatever path it is given; the toolkit's save
        restores them, and no call site here may have to remember that.
        """
        design_dir = os.path.dirname(os.path.abspath(layout.__file__))
        offenders = []
        for name in sorted(os.listdir(design_dir)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(design_dir, name)
            with open(path, encoding="utf-8") as handle:
                if "pcbnew.SaveBoard(" in handle.read():
                    offenders.append(name)
        self.assertEqual(offenders, [])

    def test_pin_assignment_is_unique(self):
        mapping = netlist.pin_to_net()
        self.assertEqual(len(mapping),
                         sum(len(pins) for pins in netlist.NETS.values()))

    def test_every_symbol_pin_is_connected_or_declared_no_connect(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        mapping = netlist.pin_to_net()
        declared = set(netlist.NO_CONNECT)
        unresolved = []
        for reference, part in netlist.PARTS.items():
            for number in library.pins(part["lib_id"]):
                pin_ref = "%s.%s" % (reference, number)
                if pin_ref not in mapping and pin_ref not in declared:
                    unresolved.append(pin_ref)
        self.assertEqual(unresolved, [])

    def test_declared_pins_exist_on_the_symbol(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        missing = []
        for pin_ref in list(netlist.pin_to_net()) + list(netlist.NO_CONNECT):
            reference, _, number = pin_ref.partition(".")
            lib_id = netlist.PARTS[reference]["lib_id"]
            if number not in library.pins(lib_id):
                missing.append(pin_ref)
        self.assertEqual(missing, [])

    def test_the_library_holds_nothing_the_design_source_does_not_write(self):
        produced = set(libraries.artifacts())
        present = {libraries.SYMBOL_LIB_PATH}
        for root, _, names in os.walk(libraries.FOOTPRINT_DIR):
            for name in names:
                present.add(os.path.join(root, name))
        self.assertEqual(sorted(present - produced), [])

    def test_the_committed_design_files_are_the_generated_ones(self):
        with open(build.schematic_path(), "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), build.generate_schematic_text())
        for path, text in libraries.artifacts().items():
            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), text, path)

    def test_every_part_the_bom_carries_names_a_footprint(self):
        for reference, part in netlist.PARTS.items():
            if part["in_bom"]:
                self.assertTrue(part["footprint"], reference)


class BusChain(unittest.TestCase):
    """The order the bus meets things in is the whole of its protection."""

    def setUp(self):
        self.mapping = netlist.pin_to_net()

    def test_the_pair_reaches_the_transceiver_and_nothing_else_active(self):
        for net, protector, transceiver in (("CANH", "D4.1", "U2.7"),
                                            ("CANL", "D4.2", "U2.6")):
            pins = set(netlist.NETS[net])
            self.assertIn(protector, pins, net)
            self.assertIn(transceiver, pins, net)
            controller = {pin for pin in pins if pin.startswith("U1.")}
            self.assertEqual(controller, set(), net)

    def test_the_two_conductors_are_the_connector_s_own_adjacent_contacts(self):
        order = netlist.CONNECTOR_PIN_ORDER["J2"]
        functions = netlist.CONNECTOR_FUNCTION_NETS["J2"]
        carried = [functions[name] for name in order]
        self.assertEqual(abs(carried.index("CANH") - carried.index("CANL")), 1)
        self.assertEqual(carried[0], netlist.GROUND_NET)

    def test_the_termination_is_split_and_its_centre_is_decoupled(self):
        self.assertEqual(self.mapping["R9.1"], "CANH")
        self.assertEqual(self.mapping["R10.1"], "CANL")
        self.assertEqual(self.mapping["R9.2"], "TERM_H")
        self.assertEqual(self.mapping["R10.2"], "TERM_L")
        self.assertEqual(self.mapping["C20.1"], "TERM_SPLIT")
        self.assertEqual(self.mapping["C20.2"], netlist.GROUND_NET)

    def test_each_leg_carries_its_own_link_so_neither_half_is_stranded(self):
        for reference, leg in (("J6", "TERM_H"), ("J7", "TERM_L")):
            pins = {number: net for number, net
                    in netlist.CONNECTOR_FUNCTION_NETS[reference].items()}
            self.assertEqual(sorted(pins.values()), sorted([leg,
                                                            "TERM_SPLIT"]))

    def test_the_transceiver_s_mode_is_defined_without_the_controller(self):
        """The mode pin carries a resistor to the reference, not a wish.

        The controller drives it, but the controller is absent while the
        board is powered and held in reset, and a floating mode pin on this
        device is neither mode. The pull decides what the transceiver does
        in that window; the controller only changes it afterwards.
        """
        self.assertEqual(self.mapping["R8.2"], netlist.GROUND_NET)
        self.assertEqual(self.mapping["R8.1"], "CAN_STB")
        self.assertEqual(self.mapping["U2.8"], "CAN_STB")
        self.assertEqual(
            self.mapping["U1.%s" % netlist.TRANSCEIVER_STANDBY_PIN],
            "CAN_STB")

    def test_the_declared_rates_are_the_ones_the_rules_are_judged_against(self):
        self.assertGreater(netlist.DATA_PHASE_RATE_BPS,
                           netlist.ARBITRATION_RATE_BPS)


class FieldChannels(unittest.TestCase):
    def setUp(self):
        self.mapping = netlist.pin_to_net()

    def test_every_output_has_its_own_switch_clamp_and_contact(self):
        for channel in range(1, netlist.OUTPUT_COUNT + 1):
            net = "DO%d" % channel
            self.assertEqual(self.mapping["Q%d.3" % (channel + 1)], net)
            self.assertEqual(self.mapping["D%d.1" % (channel + 8)], net)
            self.assertEqual(self.mapping["J3.%d" % (channel + 1)], net)

    def test_every_input_has_its_own_divider_clamp_and_filter(self):
        for channel in range(1, netlist.INPUT_COUNT + 1):
            self.assertEqual(self.mapping["J4.%d" % (channel + 1)],
                             "DI%d" % channel)
            self.assertEqual(self.mapping["R%d.1" % (channel + 13)],
                             "DI%d" % channel)
            divided = self.mapping["R%d.2" % (channel + 13)]
            self.assertEqual(self.mapping["R%d.1" % (channel + 17)], divided)
            self.assertEqual(self.mapping["C%d.1" % (channel + 20)], divided)
            self.assertEqual(self.mapping["D%d.2" % (channel + 4)], divided)
            self.assertEqual(self.mapping["D%d.1" % (channel + 4)],
                             netlist.LOGIC_RAIL_NET)

    def test_a_channel_reaches_no_other_channel(self):
        shared = set(netlist.POWER_NETS) | {netlist.GROUND_NET}
        for channel in range(1, netlist.OUTPUT_COUNT + 1):
            own = {"Q%d" % (channel + 1), "D%d" % (channel + 8)}
            for net, pins in netlist.NETS.items():
                if net in shared:
                    continue
                touching = {pin.split(".")[0] for pin in pins} & own
                if not touching:
                    continue
                for pin in pins:
                    reference = pin.split(".")[0]
                    self.assertFalse(
                        re.match(r"^(Q|D)\d+$", reference)
                        and reference not in own
                        and reference in
                        {"Q%d" % (other + 1) for other in
                         range(1, netlist.OUTPUT_COUNT + 1)},
                        "%s joins %s" % (net, reference))

    def test_the_controller_pin_each_channel_uses_is_the_declared_one(self):
        for index, pin in enumerate(netlist.OUTPUT_PINS, start=1):
            self.assertEqual(self.mapping["U1.%s" % pin], "DO%d_DRV" % index)
        for index, pin in enumerate(netlist.INPUT_PINS, start=1):
            self.assertEqual(self.mapping["U1.%s" % pin], "DI%d_IN" % index)


class Protection(unittest.TestCase):
    def test_every_entering_conductor_is_clamped_or_excused(self):
        parameters = rules.load_parameters()
        for result in rules.evaluate_protection_coverage(parameters):
            self.assertEqual(result["claim"]["quantity"]["value"], 0.0)

    def test_every_excused_conductor_states_why(self):
        for net, reason in netlist.PROTECTION_EXEMPT.items():
            self.assertIn(net, netlist.NETS, net)
            self.assertGreater(len(reason.split()), 3, net)

    def test_the_excused_set_names_only_conductors_that_enter(self):
        entering = set(netlist.entering_conductors())
        self.assertEqual(sorted(set(netlist.PROTECTION_EXEMPT) - entering), [])

    def test_the_reference_is_the_one_every_clamp_diverts_into(self):
        mapping = netlist.pin_to_net()
        for reference, part in netlist.PARTS.items():
            if part.get("mpn") != "ESDCAN05-2BWY":
                continue
            self.assertEqual(mapping["%s.3" % reference], netlist.GROUND_NET)


class Evidence(unittest.TestCase):
    def test_the_frozen_documents_are_intact_and_all_referenced(self):
        self.assertEqual(evidence.verify(), [])

    def test_the_committed_index_is_the_computed_one(self):
        self.assertEqual(evidence.load_index(), evidence.compute_index())

    def test_every_parameter_names_a_frozen_document(self):
        known = set(evidence.load_index()["documents"])
        unknown = set()

        def walk(node):
            if isinstance(node, dict):
                document = node.get("document")
                if isinstance(document, str) and document not in known:
                    unknown.add(document)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(rules.load_parameters()["parts"])
        self.assertEqual(sorted(unknown), [])

    def test_every_bom_part_has_frozen_parameters_and_a_catalogue_entry(self):
        parameters = rules.load_parameters()["parts"]
        catalog = rules.load_catalog()["parts"]
        for reference, part in netlist.PARTS.items():
            if not part["in_bom"]:
                continue
            self.assertIn(part["mpn"], parameters, reference)
            self.assertIn(part["lcsc"], catalog, reference)

    def test_the_catalogue_holds_no_part_the_board_does_not_use(self):
        used = {part["lcsc"] for part in netlist.PARTS.values()
                if part["in_bom"]}
        self.assertEqual(sorted(set(rules.load_catalog()["parts"]) - used), [])


class Requirements(unittest.TestCase):
    def setUp(self):
        self.results = rules.evaluate_all()

    def test_no_board_rule_fails(self):
        failed = sorted(result["id"] for result in self.results
                        if result["verdict"]["result"] == "FAIL")
        self.assertEqual(failed, [])

    def test_no_board_rule_is_unresolved(self):
        unknown = sorted(result["id"] for result in self.results
                         if result["verdict"]["result"] == "UNKNOWN")
        self.assertEqual(unknown, [])

    def test_the_committed_requirement_evidence_is_current(self):
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            committed = json.load(handle)
        rules.write_report()
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(committed, json.load(handle))

    def test_every_claim_carries_its_own_provenance(self):
        for result in self.results:
            evidence_block = result["claim"]["evidence"]
            self.assertIn("provenance", evidence_block, result["id"])
            self.assertTrue(evidence_block["provenance"]["source"],
                            result["id"])

    def test_every_probe_required_net_exists(self):
        for net in netlist.PROBE_REQUIRED_NETS:
            self.assertIn(net, netlist.NETS)

    def test_the_assembly_policy_is_what_the_board_holds(self):
        measured = {result["id"]: result["claim"]["quantity"]["value"]
                    for result in self.results}
        self.assertEqual(
            measured["hand_soldered_part_count_matches_the_assembly_policy"],
            float(netlist.ASSEMBLY_POLICY["through_hole_soldered_parts"]))
        self.assertEqual(netlist.ASSEMBLY_POLICY["hand_fitted_parts"],
                         netlist.TERMINATION_LINK["count"])
        self.assertEqual(netlist.ASSEMBLY_POLICY["placement_sides"], 1)


class Supply(unittest.TestCase):
    def test_stock_covers_the_planned_build(self):
        limits = cost.stock_limited_boards()
        self.assertGreaterEqual(min(limits.values()),
                                netlist.PLANNED_BUILD_QUANTITY)

    def test_every_bom_line_prices(self):
        report = cost.bom_cost(netlist.PLANNED_BUILD_QUANTITY)
        self.assertGreater(report["per_board_usd"], 0.0)
        self.assertEqual(len(report["lines"]), len(cost.line_items()))


class Scenarios(unittest.TestCase):
    def setUp(self):
        self.documents = simulation.documents()

    def test_every_scenario_validates(self):
        for _, document in self.documents.items():
            sim_scenario.validate_scenario(document)

    def test_the_committed_scenarios_are_the_generated_ones(self):
        present = sorted(os.listdir(simulation.SIM_DIR))
        self.assertEqual(present, sorted(self.documents))
        for name, document in self.documents.items():
            with open(os.path.join(simulation.SIM_DIR, name), "r",
                      encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), document, name)

    def test_every_scenario_runs_and_every_assertion_holds(self):
        backend = ngspice.backend_identity()
        if not backend["available"]:
            self.skipTest("no ngspice backend: " + backend["detail"])
        registry = extraction.simulation_registry()
        work = os.path.join(REPO_ROOT, "out", "sim")
        for name, document in sorted(self.documents.items()):
            result = ngspice.run_scenario(
                registry, document, os.path.join(work, document["name"]))
            self.assertEqual(result["status"], "ran", name)
            self.assertTrue(result["converged"], name)
            for measurement, record in result["measurements"].items():
                verdict = record["verdict"]
                if verdict is None:
                    continue
                self.assertEqual(verdict["result"], "PASS",
                                 "%s: %s" % (name, measurement))


class Extraction(unittest.TestCase):
    """The board's own copper, measured rather than budgeted."""

    def setUp(self):
        self.document = extraction.load()

    def test_the_committed_extraction_describes_the_committed_board(self):
        self.assertEqual(self.document["board_file_sha256"],
                         extraction.board_digest())

    def test_the_physical_inputs_are_the_committed_ones(self):
        with open(physical.PHYSICAL_PATH, "r", encoding="utf-8") as handle:
            committed = json.load(handle)
        self.assertEqual(committed, physical.document())
        self.assertEqual(self.document["physical_inputs"], committed)

    def test_every_traced_path_is_one_the_netlist_holds(self):
        mapping = netlist.pin_to_net()
        for record in self.document["paths"]:
            for pad in record["pads"]:
                self.assertEqual(mapping[pad], record["net"], pad)

    def test_no_traced_path_crosses_a_layer_the_copper_is_not_priced_on(self):
        priced = set(self.document["physical_inputs"]["copper_thickness_mm"])
        for record in self.document["paths"]:
            for hop in record["hops"]:
                self.assertEqual(
                    sorted(set(hop["length_by_layer_mm"]) - priced), [],
                    record["net"])

    def test_the_measured_copper_is_inside_the_budget_it_was_priced_at(self):
        for net, ohms in extraction.resistances().items():
            self.assertLessEqual(ohms, netlist.BOARD_COPPER_BUDGET_OHM, net)

    def test_every_declared_extracted_model_names_a_traced_conductor(self):
        declared = manifest.extracted_models()
        mapping = netlist.pin_to_net()
        for alias, path in declared["paths"].items():
            for key in ("from_pad", "to_pad"):
                self.assertEqual(mapping[path[key]], path["net"],
                                 "%s: %s" % (alias, key))
        self.assertTrue(os.path.isfile(
            os.path.join(REPO_ROOT, declared["physical_inputs"])))


class Manifest(unittest.TestCase):
    def setUp(self):
        self.document = manifest.document()

    def _has(self, dotted):
        cursor = self.document
        for part in dotted.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return False
            cursor = cursor[part]
        return True

    def test_the_committed_manifest_is_the_generated_one(self):
        with open(manifest.MANIFEST_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), self.document)

    def test_every_connector_contract_matches_the_netlist(self):
        mapping = netlist.pin_to_net()
        for contract in self.document["connector_contracts"]:
            reference = contract["reference"]
            for number, net in contract["pin_map"].items():
                self.assertEqual(mapping["%s.%s" % (reference, number)], net)

    def test_the_constraint_floor_is_what_the_project_is_written_with(self):
        floor = self.document["checks"]["drc"]["constraint_floor"]
        self.assertEqual(floor["rules"], build.DESIGN_RULES)
        for entry in build.NET_CLASSES:
            self.assertIn(entry["name"], floor["net_classes"])

    def test_every_stage_the_manifest_requires_carries_a_scenario(self):
        stages = self.document["simulation"]["stages"]
        for stage in self.document["simulation"]["required_stages"]:
            self.assertTrue(stages.get(stage), stage)
        self.assertIn("post_layout", stages)

    def test_every_declared_scenario_file_exists(self):
        for stage, names in self.document["simulation"]["stages"].items():
            for name in names:
                self.assertTrue(
                    os.path.isfile(os.path.join(REPO_ROOT, name)),
                    "%s: %s" % (stage, name))
        for stage in self.document["simulation"]["required_stages"]:
            self.assertIn(stage, self.document["simulation"]["stages"])

    def test_every_placement_rule_counts_what_the_netlist_holds(self):
        for rule in self.document["placement_rules"]:
            pattern = re.compile(rule["reference_regex"])
            found = [reference for reference in netlist.PARTS
                     if pattern.match(reference)]
            self.assertEqual(len(found), rule["count"], rule["id"])

    def test_no_domain_is_both_declared_and_declined(self):
        """A decline is a decision, and a declared domain has made another.

        The policy machinery refuses a manifest that does both, and it
        refuses it at validation time - after a rebuild. This says so from
        the source, where the decline is written.
        """
        from pcbqa import policy
        declined = {entry["domain"]
                    for entry in
                    self.document["release_profile"]["declined_domains"]}
        for domain in sorted(declined):
            self.assertIn(domain, policy.DOMAINS, domain)
            for key in policy.DOMAINS[domain]["declared_by"]:
                self.assertFalse(self._has(key),
                                 "%s is declined and declares %s"
                                 % (domain, key))

    def test_every_required_domain_is_one_the_manifest_declares(self):
        from pcbqa import policy
        for domain in self.document["release_profile"]["required_domains"]:
            self.assertIn(domain, policy.DOMAINS, domain)
            self.assertTrue(
                any(self._has(key)
                    for key in policy.DOMAINS[domain]["declared_by"]),
                "%s is required and declared by nothing" % domain)

    def test_the_continuity_routes_are_the_pair_the_topology_rule_holds(self):
        """The two declarations describe one pair, or one of them is stale.

        `BUS_PAIR` says the pair takes no via and stays on the front layer;
        the continuity declaration says the reference stays under it. They
        are two halves of one requirement, written apart, so this is what
        stops them describing different conductors.
        """
        rule = [entry for entry in self.document["net_topology"]["rules"]
                if entry["id"] == "BUS_PAIR"][0]
        nets = re.compile(rule["net_regex"])
        mapping = netlist.pin_to_net()

        def pads(pattern):
            expression = re.compile(pattern)
            return sorted(pin for pin in mapping if expression.match(pin))

        paths = self.document["reference_continuity"]["paths"]
        self.assertEqual(len(paths), 2)
        for name, path in sorted(paths.items()):
            step, = path["steps"]
            self.assertEqual(step["kind"], "copper", name)
            self.assertTrue(nets.match(step["net"]), name)
            for key, rule_key in (("from", "source_pad_regex"),
                                  ("to", "load_pad_regex")):
                self.assertTrue(
                    set(pads(step[key])) <= set(pads(rule[rule_key])),
                    "%s: %s is not one of the pads BUS_PAIR names"
                    % (name, key))
        self.assertEqual(
            sorted(pad for path in paths.values() for step in path["steps"]
                   for key in ("from", "to") for pad in pads(step[key])),
            sorted(pads(rule["source_pad_regex"])
                   + pads(rule["load_pad_regex"])),
            "the routes and the topology rule cover different pads")

    def test_every_continuity_route_ends_on_pads_that_carry_its_net(self):
        mapping = netlist.pin_to_net()
        for name, path in self.document["reference_continuity"][
                "paths"].items():
            for step in path["steps"]:
                for key in ("from", "to"):
                    pattern = re.compile(step[key])
                    matched = [pin for pin in mapping
                               if pattern.match(pin)]
                    self.assertEqual(len(matched), 1,
                                     "%s: %s" % (name, key))
                    self.assertEqual(mapping[matched[0]], step["net"],
                                     "%s: %s" % (name, key))

    def test_the_reference_net_is_the_one_the_back_layer_pours(self):
        poured = {entry["plane_net"]
                  for entry in self.document["stackup"]["expected"]}
        for net in self.document["reference_continuity"]["reference_nets"]:
            self.assertIn(net, poured, net)
        self.assertEqual(
            self.document["reference_continuity"]["reference_nets"],
            [netlist.GROUND_NET])

    def test_the_catalog_pin_is_the_state_the_fabrication_was_selected_at(
            self):
        """A cited limit is pinned to the reviewed catalogue or it is not one.

        The same digest the process selection recorded and the physical
        inputs already carry: three citations of one catalogue state, which
        can only stay one state if they are checked against each other.
        """
        with open(os.path.join(REPO_ROOT, "fab", "selection.json"),
                  "r", encoding="utf-8") as handle:
            selection = json.load(handle)
        pinned = self.document["catalog"]["normalized_sha256"]
        self.assertEqual(pinned, selection["approved_normalized_sha256"])
        self.assertEqual(pinned,
                         physical.approved_snapshot()["normalized_sha256"])
        for record in physical.document()["copper_thickness_mm"].values():
            self.assertEqual(record["digest"], pinned)

    def test_every_topology_rule_names_pads_the_netlist_holds(self):
        mapping = netlist.pin_to_net()
        for rule in self.document["net_topology"]["rules"]:
            nets = re.compile(rule["net_regex"])
            self.assertTrue([net for net in netlist.NETS if nets.match(net)],
                            rule["id"])
            for key in ("source_pad_regex", "load_pad_regex"):
                pattern = re.compile(rule[key])
                matched = [pin for pin in mapping if pattern.match(pin)]
                self.assertTrue(matched, "%s: %s" % (rule["id"], key))
                for pin in matched:
                    self.assertTrue(nets.match(mapping[pin]),
                                    "%s: %s" % (rule["id"], pin))


class Thermal(unittest.TestCase):
    """The dissipation inventory, and where each of its numbers came from."""

    def setUp(self):
        self.parameters = rules.load_parameters()
        self.document = thermal.document(self.parameters)
        self.parts = self.document["parts"]

    def test_the_ambient_is_the_one_the_board_s_ratings_are_claimed_at(self):
        self.assertEqual(self.document["ambient_c"], netlist.AMBIENT_MAX_C)

    def test_every_declared_part_carries_a_junction_path_and_a_maximum(self):
        """Both, or the part may not be derated at all.

        A thermal resistance with no junction maximum has nothing to be
        judged against, and a junction maximum with no resistance gives no
        rise to judge; the gate refuses either, and so does this.
        """
        for reference, part in sorted(self.parts.items()):
            self.assertIn("junction_max_c", part, reference)
            self.assertIn("theta_ja", part, reference)
            self.assertEqual(part["theta_ja"]["units"], "C/W", reference)
            self.assertGreater(part["dissipation_w"], 0.0, reference)

    def test_every_thermal_figure_is_the_parameter_store_s(self):
        for reference, part in sorted(self.parts.items()):
            spec = rules._spec(self.parameters, reference)["thermal"]
            self.assertEqual(part["theta_ja"]["value"],
                             spec["rthja_c_per_w"]["value"], reference)
            self.assertEqual(part["junction_max_c"],
                             spec["tj_max_c"]["value"], reference)
            for document in part["documents"]:
                self.assertIn(document, evidence.load_index()["documents"],
                              reference)

    def test_the_regulator_s_share_is_the_one_its_own_claim_is_made_from(self):
        """One number, two consumers: the claim and the thermal declaration.

        The claim judges the linear stage against its package rating at 25
        C; the declaration derates the same dissipation at 60 C. If the two
        ever disagree the board is making two statements about one part.
        """
        with open(os.path.join(REPO_ROOT, "generated", "requirements.json"),
                  "r", encoding="utf-8") as handle:
            document = json.load(handle)
        claimed = [entry for entry in document["results"]
                   if entry["id"]
                   == "linear_stage_within_its_package_dissipation"]
        self.assertEqual(len(claimed), 1)
        self.assertAlmostEqual(claimed[0]["claim"]["quantity"]["value"],
                               self.parts["U4"]["dissipation_w"], places=12)

    def test_the_parts_left_out_have_no_steady_state_figure_to_leave_in(self):
        """The exclusions are a fact about the datasheets, not a preference.

        Every switching FET on this board publishes its thermal resistance
        under a ten-second test condition. If one of them ever gains a
        steady-state figure, this test fails and the part belongs in the
        inventory.
        """
        switches = sorted({netlist.PARTS[reference]["mpn"]
                           for reference in netlist.PARTS
                           if reference.startswith("Q")})
        self.assertTrue(switches)
        for mpn in switches:
            thermal_group = self.parameters["parts"][mpn].get("thermal", {})
            self.assertNotIn("rthja_c_per_w", thermal_group, mpn)
            self.assertIn("power_max_w", thermal_group, mpn)
        for reference in self.parts:
            self.assertNotIn(netlist.PARTS[reference]["mpn"], switches)


class Board(unittest.TestCase):
    def test_every_part_with_a_footprint_has_a_seed_pose(self):
        placed = layout.seed_placement()
        missing = sorted(reference for reference, part in netlist.PARTS.items()
                         if part["footprint"] and reference not in placed)
        self.assertEqual(missing, [])

    def test_the_locked_set_is_the_board_s_mechanical_and_service_contract(
            self):
        expected = {"C20", "D4", "R9", "R10", "U2"}
        for reference, part in netlist.PARTS.items():
            if not part["footprint"]:
                continue
            if re.match(r"^(J|H|TP)\d+$", reference):
                expected.add(reference)
        self.assertEqual(set(layout.LOCKED_REFERENCES), expected)

    def test_the_bus_stations_stand_in_the_order_the_bus_meets_them(self):
        self.assertLess(layout.BUS_PROTECTOR_Y_MM,
                        layout.BUS_TERMINATION_Y_MM)
        self.assertLess(layout.BUS_TERMINATION_Y_MM,
                        layout.BUS_TRANSCEIVER_Y_MM)

    def test_the_protected_return_under_the_pair_is_not_broken_at_a_station(
            self):
        stations = (layout.BUS_PROTECTOR_Y_MM, layout.BUS_TERMINATION_Y_MM,
                    layout.BUS_TRANSCEIVER_Y_MM)
        for low, high in layout.BUS_KEEPOUT_SPANS_MM:
            self.assertLess(low, high)
            for station in stations:
                self.assertFalse(low <= station <= high,
                                 "%s covers %s" % ((low, high), station))

    def test_the_board_outline_holds_every_seed(self):
        for reference, (x, y, _) in layout.seed_placement().items():
            self.assertTrue(0.0 < x < layout.BOARD_W_MM, reference)
            self.assertTrue(0.0 < y < layout.BOARD_H_MM, reference)

    def test_the_switching_loop_is_shorter_than_the_board(self):
        """The catch diode is beside the converter, not across the board."""
        placed = layout.seed_placement()
        converter = placed["U3"]
        for reference in ("D3", "C4", "C5"):
            part = placed[reference]
            span = math_hypot(part[0] - converter[0], part[1] - converter[1])
            self.assertLess(span, 10.0, reference)


def math_hypot(dx, dy):
    return (dx * dx + dy * dy) ** 0.5


class StaticVerification(unittest.TestCase):
    def test_the_schematic_passes_erc(self):
        report = os.path.join(REPO_ROOT, "out", "erc_test.json")
        os.makedirs(os.path.dirname(report), exist_ok=True)
        completed = subprocess.run(
            ["kicad-cli", "sch", "erc", "--output", report, "--format",
             "json", "--severity-error", "--severity-warning",
             "--exit-code-violations", build.schematic_path()],
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        with open(report, "r", encoding="utf-8") as handle:
            document = json.load(handle)
        violations = [violation for sheet in document.get("sheets", [])
                      for violation in sheet.get("violations", [])]
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
