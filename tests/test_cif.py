#!/usr/bin/env python

import gc
import os
import unittest
from gemmi import cif

class TestBlock(unittest.TestCase):
    def test_find(self):
        block = cif.read_string("""
            data_test
            _one 1 _two 2 _three 3
            _nonloop_a alpha
            _nonloop_b beta
            loop_ _la _lb _ln A B 1 C D 2
        """).sole_block()
        gc.collect()
        values = block.find_values('_la')
        self.assertEqual(list(values), ['A', 'C'])

        rows = list(block.find(['_lb', '_la']))  # changed order
        gc.collect()
        self.assertEqual(list(rows[0]), ['B', 'A'])
        self.assertEqual(rows[1][1], 'C')

        rows = list(block.find('_nonloop_', ['a', 'b']))
        gc.collect()
        self.assertEqual([list(r) for r in rows], [['alpha', 'beta']])

        tab = block.find(['_la', '_ln'])
        self.assertEqual(tab.find_row('A')[1], '1')
        self.assertRaises(RuntimeError, tab.find_row, 'B')
        self.assertEqual(tab.find_row('C')[1], '2')
        self.assertEqual(tab.column(0)[1], 'C')
        self.assertEqual(tab.column(1)[0], '1')
        self.assertEqual(tab.find_column('a')[1], 'C')
        self.assertEqual(tab.find_column('_ln')[0], '1')

        tab = block.find(['_lb', '_ln'])
        self.assertRaises(RuntimeError, tab.find_row, 'A')
        self.assertEqual(tab.find_row('B')[1], '1')
        self.assertEqual(tab.find_row('D')[1], '2')

        tab = block.find(['_la', '?_nop', '?_ln'])
        self.assertEqual(len(tab), 2)
        self.assertEqual(tab.width(), 3)
        row = tab[0]
        self.assertIsNotNone(row.get(0))
        self.assertEqual(row[0], 'A')
        self.assertIsNone(row.get(1))
        self.assertEqual(row[2], '1')
        self.assertTrue("None" in repr(row))

    def test_find_values(self):
        v1 = cif.read_string('data_a _v1 one')[0].find_values('_v1')
        gc.collect()
        self.assertListEqual(list(v1), ['one'])
        v2 = cif.read_string('data_a loop_ _v2 a b')[0].find_values('_v2')
        gc.collect()
        self.assertListEqual(list(v2), ['a', 'b'])

    def test_set_pair(self):
        doc = cif.read_string('data_a _a 1 _b 2 _c 3')
        block = doc[0]
        block.set_pair('_d', '9')
        block.set_pair('_b', '8')
        self.assertEqual(block.find_pair('_a'), ['_a', '1'])
        self.assertEqual(block.find_value('_b'), '8')
        self.assertEqual(block.find_value('_c'), '3')
        self.assertEqual(block.find_value('_d'), '9')

    def test_set_loop(self):
        block = cif.read_string('data_a _c.a 1 _c.b 2 _c.c 3 loop_ _cx.b 3')[0]
        block.init_loop('_cx.', ['b']).add_row(['x'])
        self.assertEqual(block.find_value('_c.a'), '1')
        block.init_mmcif_loop('_c.', ['c']).add_row(['y'])
        self.assertEqual(block.find_value('_c.a'), None)
        loop = block.init_loop('_c.', ['c', 'd'])
        loop.set_all_values([list('one'), list('two')])
        self.assertEqual(loop.width(), 2)
        self.assertEqual(loop.length(), 3)
        self.assertEqual(list(block.find(['_c.c', '_c.d'])[1]), ['n', 'w'])

    def test_setitem(self):
        block = cif.read_string('data_a _a 1 _b 2 _c 3')[0]
        self.assertEqual(block.find_value('_b'), '2')
        col_b = block.find_values('_b')
        col_b[0] = '20'
        self.assertEqual(block.find_value('_b'), '20')
        bc = block.find(['_b', '_a'])
        bc[0][0] = '30'
        self.assertEqual(block.find_value('_b'), '30')
        bc[0][1] = '40'
        self.assertEqual(block.find_value('_a'), '40')

    def test_add_row(self):
        block = cif.read_string('data_a loop_ _x _y 1 2 3 4')[0]
        loop = block.find_loop('_x').get_loop()
        loop.add_row(['5', '6'])
        loop.add_row(['?', '0'], 0)
        self.assertEqual(list(block.find_values('_y')), '0 2 4 6'.split())

    def test_set_mmcif_category(self):
        doc = cif.Document()
        block = doc.add_new_block('b')
        block.set_mmcif_category('_c', {
            'one': ('?', 'ab', ';text field\n;'),
            'two': [-1, 4./3, '"double quoted"']}, raw=True)
        self.assertEqual(block.find_values('_c.one')[0], '?')
        self.assertEqual(block.find_values('_c.one').str(1), 'ab')
        self.assertEqual(block.find_values('_c.one').str(2), 'text field')
        self.assertEqual(block.find_values('_c.two').str(0), '-1')
        self.assertEqual(block.find_values('_c.two').str(2), 'double quoted')
        block.set_mmcif_category('_d', {
            'one': (None, 'a b', 'text\nfield'),
            'two': [-1, '?', False]})
        self.assertEqual(block.find_values('_d.one')[0], '?')
        self.assertEqual(block.find_values('_d.two').str(1), '?')
        self.assertEqual(block.find_values('_d.one').str(1), 'a b')
        self.assertEqual(block.find_values('_d.one').str(2), 'text\nfield')
        self.assertEqual(block.find_values('_d.one')[2], ';text\nfield\n;')
        self.assertEqual(block.find_values('_d.two').str(0), '-1')
        self.assertEqual(block.find_values('_d.two')[2], '.')

    def test_mmcif_file(self):
        path = os.path.join(os.path.dirname(__file__), '5i55.cif')
        block = cif.read(path).sole_block()
        self.assertEqual(len(block.get_mmcif_category_names()), 54)

    def test_reading_gzipped_file(self):
        path = os.path.join(os.path.dirname(__file__), '1pfe.cif.gz')
        cif_doc = cif.read(path)
        block = cif_doc.sole_block()
        categories = block.get_mmcif_category_names()
        self.assertEqual(categories[0], '_entry.')
        self.assertEqual(len(categories), 72)
        exptl = block.find_mmcif_category('_exptl')
        self.assertEqual(list(exptl.tags), ['_exptl.entry_id', '_exptl.method',
                                            '_exptl.crystals_number'])
        self.assertEqual(len(exptl), 1)
        self.assertEqual(exptl.width(), 3)
        exptl = block.find_mmcif_category('_exptl')
        self.assertEqual(len(exptl), 1)
        self.assertEqual(exptl.width(), 3)
        self.assertEqual(exptl[0].str(1), 'X-RAY DIFFRACTION')
        struct_asym = block.find_mmcif_category('_struct_asym')
        self.assertEqual(len(struct_asym), 7)
        self.assertEqual(struct_asym.width(), 5)
        self.assertListEqual(list(struct_asym[3]), ['D', 'N', 'N', '4', '?'])
        nonexistent = block.find_mmcif_category('_nonexistent')
        self.assertEqual(len(nonexistent), 0)
        self.assertEqual(nonexistent.width(), 0)

if __name__ == '__main__':
    unittest.main()