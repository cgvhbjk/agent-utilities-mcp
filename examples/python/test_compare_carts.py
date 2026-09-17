import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import compare_carts as recipe


def fixture():
    return json.loads(Path(__file__).with_name('cart_comparison_example.json').read_text())


def result(total, *, missing=None):
    return {'currency': 'USD', 'minorUnitDigits': 2, 'knownTotal': total,
            'total': None if missing else total, 'missingComponents': missing or [],
            'matchesDeclaredTotal': None}


class CartComparisonTest(unittest.TestCase):
    def test_preview_never_contacts_service_or_reads_key(self):
        output = io.StringIO()
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected HTTP')), \
                patch.object(recipe, 'Client', side_effect=AssertionError('Unexpected key access')), \
                contextlib.redirect_stdout(output):
            recipe.main([])
        preview = json.loads(output.getvalue())
        self.assertEqual(preview['mode'], 'offline-preview')
        self.assertEqual(preview['maxNewDebitMicroUsd'], 1000)
        self.assertEqual(len(preview['calls']), 2)

    def test_shipping_reverses_item_price_ranking_and_ties_are_preserved(self):
        plan = recipe.prepare_comparison(fixture())
        compared = recipe.compare_results(plan, [result('25.49'), result('22.50')])
        self.assertEqual(compared['overallCheapestIds'], ['free-shipping'])
        self.assertEqual(compared['completeRanking'], ['free-shipping', 'lower-item-price'])
        compared = recipe.compare_results(plan, [result('22.50'), result('22.50')])
        self.assertEqual(compared['overallCheapestIds'], ['lower-item-price', 'free-shipping'])

    def test_unknown_costs_prevent_overall_winner_and_stay_out_of_ranking(self):
        data = fixture()
        data['carts'][0]['tax'] = None
        plan = recipe.prepare_comparison(data)
        compared = recipe.compare_results(plan, [result('23.99', missing=['tax']), result('22.50')])
        self.assertIsNone(compared['overallCheapestIds'])
        self.assertEqual(compared['cheapestCompleteIds'], ['free-shipping'])
        self.assertEqual(compared['incompleteIds'], ['lower-item-price'])
        data['carts'][1]['shipping'] = None
        compared = recipe.compare_results(recipe.prepare_comparison(data),
                                          [result('23.99', missing=['tax']), result('22.50', missing=['shipping'])])
        self.assertEqual(compared['completeRanking'], [])

    def test_exact_comparison_above_float_precision(self):
        data = fixture()
        data['minorUnitDigits'] = 6
        plan = recipe.prepare_comparison(data)
        a, b = result('99999999999999999.000002'), result('99999999999999999.000001')
        a['minorUnitDigits'] = b['minorUnitDigits'] = 6
        self.assertEqual(recipe.compare_results(plan, [a, b])['overallCheapestIds'], ['free-shipping'])

    def test_invalid_later_cart_or_budget_rejected_before_preparing_calls(self):
        for mutate in [
            lambda v: v['carts'][1].update(id=v['carts'][0]['id']),
            lambda v: v['carts'][1].update(tax='0.001'),
            lambda v: v['carts'][1].update(currency='EUR'),
            lambda v: v['carts'][1]['items'][0].update(quantity=True),
            lambda v: v['carts'][1]['items'][0].update(discount='999.00'),
            lambda v: v['carts'][1].update(orderDiscount='999.00'),
            lambda v: v['carts'][1].update(items=[]),
        ]:
            data = fixture()
            mutate(data)
            with patch.object(recipe, 'prepare_call', side_effect=AssertionError('Prepared too early')):
                with self.assertRaises(ValueError):
                    recipe.prepare_comparison(data)
        with self.assertRaises(ValueError):
            recipe.prepare_comparison(fixture(), max_total_micro_usd=999)

    def test_execution_uses_frozen_calls_and_stops_on_failure_or_invalid_result(self):
        data = fixture()
        plan = recipe.prepare_comparison(data)
        data['carts'][0]['shipping'] = '0.00'
        self.assertEqual(json.loads(plan[0][1].body)['shipping'], '5.99')
        client, emit = Mock(), Mock()
        client.execute.side_effect = [{'result': result('25.49')}, {'result': result('22.50')}]
        compared = recipe.execute_comparison(plan, client, emit)
        self.assertEqual(compared['overallCheapestIds'], ['free-shipping'])
        self.assertEqual([c.args[0] for c in client.execute.call_args_list], [c for _, c in plan])
        self.assertEqual([c.max_price_micro_usd for _, c in plan], [500, 500])
        self.assertEqual(emit.call_count, 2)
        for response in [RuntimeError('uncertain fixture'), {'result': result('25.49', missing=['tax'])},
                         {'result': {**result('25.49'), 'currency': 'EUR'}},
                         {'result': {**result('25.49'), 'total': '0.00'}}]:
            client.reset_mock()
            client.execute.side_effect = [response]
            with self.assertRaises((RuntimeError, ValueError)):
                recipe.execute_comparison(plan, client, emit)
            self.assertEqual(client.execute.call_count, 1)
