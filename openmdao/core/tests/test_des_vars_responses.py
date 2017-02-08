""" Unit tests for the design_variable and response interface to system."""
from __future__ import print_function
import unittest

import numpy as np

from openmdao.api import Problem, NonlinearBlockGS
from openmdao.devtools.testutil import assert_rel_error

from openmdao.test_suite.components.sellar import SellarDerivatives, SellarDerivativesConnected

class TestDesVarsResponses(unittest.TestCase):

    def test_api_backwards_compatible(self):
        raise unittest.SkipTest("api not implemented yet")

        prob = Problem()
        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.driver = ScipyOpt()
        prob.driver.options['method'] = 'slsqp'
        prob.driver.add_design_var('x', lower=-100, upper=100)
        prob.driver.add_design_var('z', lower=-100, upper=100)
        prob.driver.add_objective('obj')
        prob.driver.add_constraint('con1')
        prob.driver.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_des_vars()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertItemsEqual(des_vars.keys(), ('x', 'z'))
        self.assertItemsEqual(obj.keys(), ('obj',))
        self.assertItemsEqual(constraints.keys(), ('con1', 'con2'))

    def test_api_on_model(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z', lower=-100, upper=100)
        prob.model.add_objective('obj')
        prob.model.add_constraint('con1')
        prob.model.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_design_vars()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertEqual(set(des_vars.keys()), {'x', 'z'})
        self.assertEqual(set(obj.keys()), {'obj'})
        self.assertEqual(set(constraints.keys()), {'con1', 'con2'})

    def test_api_response_on_model(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z', lower=-100, upper=100)
        prob.model.add_response('obj', type="obj")
        prob.model.add_response('con1', type="con")
        prob.model.add_response('con2', type="con")

        prob.setup()

        des_vars = prob.model.get_design_vars()
        responses = prob.model.get_responses()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertEqual(set(des_vars.keys()), {'x', 'z'})
        self.assertEqual(set(responses.keys()), {'obj', 'con1', 'con2'})
        self.assertEqual(set(obj.keys()), {'obj'})
        self.assertEqual(set(constraints.keys()), {'con1', 'con2'})

    def test_api_list_on_model(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z', lower=[-100, -20], upper=[100, 20])
        prob.model.add_objective('obj')
        prob.model.add_constraint('con1')
        prob.model.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_design_vars()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertEqual(set(des_vars.keys()), {'x', 'z'})
        self.assertEqual(set(obj.keys()), {'obj',})
        self.assertEqual(set(constraints.keys()), {'con1', 'con2'})

    def test_api_array_on_model(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z',
                                  lower=np.array([-100, -20]),
                                  upper=np.array([100, 20]))
        prob.model.add_objective('obj')
        prob.model.add_constraint('con1')
        prob.model.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_design_vars()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertEqual(set(des_vars.keys()), {'x', 'z'})
        self.assertEqual(set(obj.keys()), {'obj',})
        self.assertEqual(set(constraints.keys()), {'con1', 'con2'})

    def test_api_on_subsystems(self):

        prob = Problem()

        prob.model = SellarDerivativesConnected()
        prob.model.nl_solver = NonlinearBlockGS()

        px = prob.model.get_subsystem('px')
        px.add_design_var('x', lower=-100, upper=100)

        pz = prob.model.get_subsystem('pz')
        pz.add_design_var('z', lower=-100, upper=100)

        obj = prob.model.get_subsystem('obj_cmp')
        obj.add_objective('obj')

        con_comp1 = prob.model.get_subsystem('con_cmp1')
        con_comp1.add_constraint('con1')

        con_comp2 = prob.model.get_subsystem('con_cmp2')
        con_comp2.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_design_vars()
        obj = prob.model.get_objectives()
        constraints = prob.model.get_constraints()

        self.assertEqual(set(des_vars.keys()), {'px.x', 'pz.z'})
        self.assertEqual(set(obj.keys()), {'obj_cmp.obj',})
        self.assertEqual(set(constraints.keys()), {'con_cmp1.con1', 'con_cmp2.con2'})


class TestDesvarOnModel(unittest.TestCase):

    def test_desvar_affine_and_scaleradder(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=-100, upper=100, ref=1.0,
                                      scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=-100, upper=100, ref=0.0,
                                      adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=-100, upper=100, ref0=0.0,
                                      adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=-100, upper=100, ref0=0.0,
                                      scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with' \
                                                 ' scaler/adder')

    def test_desvar_affine_mapping(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100, ref0=-100.0,
                                  ref=100)
        prob.model.add_design_var('z', lower=-100, upper=100)
        prob.model.add_objective('obj')
        prob.model.add_constraint('con1')
        prob.model.add_constraint('con2')

        prob.setup()

        des_vars = prob.model.get_design_vars()


        x_ref0 = des_vars['x'].ref0
        x_ref = des_vars['x'].ref
        x_scaler = des_vars['x'].scaler
        x_adder = des_vars['x'].adder

        self.assertAlmostEqual( x_scaler*(x_ref0 + x_adder), 0.0, places=12)
        self.assertAlmostEqual( x_scaler*(x_ref + x_adder), 1.0, places=12)

    def test_desvar_invalid_name(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_design_var(42, lower=-100, upper=100, ref0=-100.0,
                                      ref=100)

        self.assertEqual(str(context.exception), 'The name argument should '
                                                 'be a string, got 42')

    def test_desvar_invalid_bounds(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_design_var('x', lower='foo', upper=[0, 100],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'Expected values of lower to be an '
                                                 'Iterable of numeric values, '
                                                 'or a scalar numeric value. '
                                                 'Got foo instead.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=0.0, upper=['a', 'b'],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'could not convert string '
                                                 'to float: \'a\'')


class TestConstraintOnModel(unittest.TestCase):

    def test_constraint_affine_and_scaleradder(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=-100, upper=100, ref=1.0,
                                      scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=-100, upper=100, ref=0.0,
                                      adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('x', lower=-100, upper=100, ref0=0.0,
                                      adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=-100, upper=100, ref0=0.0,
                                      scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with' \
                                                 ' scaler/adder')

    def test_constraint_affine_mapping(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z', lower=-100, upper=100)
        prob.model.add_objective('obj')
        prob.model.add_constraint('con1', lower=-100, upper=100, ref0=-100.0,
                                  ref=100)
        prob.model.add_constraint('con2')

        prob.setup()

        constraints = prob.model.get_constraints()

        con1_ref0 = constraints['con1'].ref0
        con1_ref = constraints['con1'].ref
        con1_scaler = constraints['con1'].scaler
        con1_adder = constraints['con1'].adder

        self.assertAlmostEqual( con1_scaler*(con1_ref0 + con1_adder), 0.0,
                                places=12)
        self.assertAlmostEqual( con1_scaler*(con1_ref + con1_adder), 1.0,
                                places=12)

    def test_constraint_invalid_name(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_design_var(42, lower=-100, upper=100, ref0=-100.0,
                                      ref=100)

        self.assertEqual(str(context.exception), 'The name argument should '
                                                 'be a string, got 42')

    def test_constraint_invalid_bounds(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_design_var('x', lower='foo', upper=[0, 100],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'Expected values of lower to'
                                                 ' be an Iterable of numeric'
                                                 ' values, or a scalar numeric'
                                                 ' value. Got foo instead.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_design_var('x', lower=0.0, upper=['a', 'b'],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'could not convert string '
                                                 'to float: \'a\'')

    def test_constraint_invalid_name(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_constraint(42, lower=-100, upper=100, ref0=-100.0,
                                      ref=100)

        self.assertEqual(str(context.exception), 'The name argument should '
                                                 'be a string, got 42')

    def test_constraint_invalid_bounds(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_constraint('con1', lower='foo', upper=[0, 100],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'Expected values of lower to be an '
                                                 'Iterable of numeric values, '
                                                 'or a scalar numeric value. '
                                                 'Got foo instead.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=0.0, upper=['a', 'b'],
                                      ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'could not convert string '
                                                 'to float: \'a\'')

    def test_constraint_invalid_indices(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=0.0, upper=5.0,
                                      indices='foo')

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=0.0, upper=5.0,
                                      indices=1)

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_constraint('con1', lower=0.0, upper=5.0,
                                      indices=[1, 'k'])

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')


class TestObjectiveOnModel(unittest.TestCase):

    def test_objective_affine_and_scaleradder(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(RuntimeError) as context:
            prob.model.add_objective('con1', lower=-100, upper=100, ref=1.0,
                                      scaler=0.5)

        self.assertEqual(str(context.exception), 'Bounds may not be set '
                                                 'on objectives')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('con1', ref=0.0, scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('con1', ref=0.0, adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('x', ref0=0.0, adder=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with'
                                                 ' scaler/adder')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('con1', ref0=0.0, scaler=0.5)

        self.assertEqual(str(context.exception), 'Inputs ref/ref0 are mutually'
                                                 ' exclusive with' \
                                                 ' scaler/adder')

    def test_objective_affine_mapping(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        prob.model.add_design_var('x', lower=-100, upper=100)
        prob.model.add_design_var('z', lower=-100, upper=100)
        prob.model.add_objective('obj', ref0=1000, ref=1010)
        prob.model.add_objective('con2')

        prob.setup()

        objectives = prob.model.get_objectives()

        obj_ref0 = objectives['obj'].ref0
        obj_ref = objectives['obj'].ref
        obj_scaler = objectives['obj'].scaler
        obj_adder = objectives['obj'].adder

        self.assertAlmostEqual( obj_scaler*(obj_ref0 + obj_adder), 0.0,
                                places=12)
        self.assertAlmostEqual( obj_scaler*(obj_ref + obj_adder), 1.0,
                                places=12)

    def test_objective_invalid_name(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(TypeError) as context:
            prob.model.add_objective(42, ref0=-100.0, ref=100)

        self.assertEqual(str(context.exception), 'The name argument should '
                                                 'be a string, got 42')

    def test_objective_invalid_indices(self):

        prob = Problem()

        prob.model = SellarDerivatives()
        prob.model.nl_solver = NonlinearBlockGS()

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('obj', indices='foo')

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('obj', indices=1)

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')

        with self.assertRaises(ValueError) as context:
            prob.model.add_objective('obj', indices=[1, 'k'])

        self.assertEqual(str(context.exception), 'If specified, indices must '
                                                 'be a sequence of integers.')