"""Rights: a Field Reports user does the whole job; only managers touch the IMSMA source and the setup."""
import base64

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

from .test_flow import FUNDED, MAC, ROWS, _package, _workbook


@tagged("post_install", "-at_install", "dma_fr")
class TestAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["dma.fr.source"].search([]).write({"is_current": False})
        # independent of what this database has learned from earlier fixes
        cls.env["dma.fr.value.map"].search([("origin", "=", "learned")]).unlink()
        cls.source = cls.env["dma.fr.source"].create({
            "name": "test package", "mode": "package", "package_file": base64.b64encode(_package()),
            "db_password": "secret"})
        cls.source.action_refresh()
        cls.user = new_test_user(cls.env, login="fr_user", groups="base.group_user,dma_field_reports.group_dma_fr_user")
        cls.manager = new_test_user(cls.env, login="fr_manager",
                                    groups="base.group_user,dma_field_reports.group_dma_fr_manager")
        cls.outsider = new_test_user(cls.env, login="fr_outsider", groups="base.group_user")

    def test_user_does_the_whole_job(self):
        env = self.env(user=self.user)
        batch = env["dma.fr.batch"].create({
            "template_id": self.env.ref("dma_field_reports.template_eore").id,
            "office_id": self.env.ref("dma_field_reports.office_dma_hq").id,
            "source_file": base64.b64encode(_workbook(ROWS)), "source_filename": "eore.xlsx"})
        batch.action_check()
        Wiz = env["dma.fr.fix.wizard"]

        def cell(row, name):
            return batch.cell_ids.filtered(lambda c: c.excel_row == row and c.field_id.name == name)

        Wiz.create({"cell_id": cell(6, "Funded by").id,
                    "option_id": env["dma.fr.ref.option"].search([("value", "=", "PMWRA"), ("cdf_ref_id.cdf_id", "=", FUNDED)]).id}).action_apply()
        Wiz.create({"cell_id": cell(6, "City / town / village").id, "place_choice": "existing",
                    "location_pick_id": env["dma.fr.ref.location"].search([("localid", "=", "LOC-CI-101")]).id}
                   ).action_apply()
        Wiz.create({"cell_id": cell(7, "Latitude").id}).action_apply()
        Wiz.create({"cell_id": cell(7, "MAC owner").id,
                    "option_id": env["dma.fr.ref.option"].search([("value", "=", "RMAC-N"), ("cdf_ref_id.cdf_id", "=", MAC)]).id}).action_apply()
        self.assertEqual(batch.error_count, 0)
        batch.action_export_locations()
        batch.action_confirm_locations()
        batch.action_export()
        self.assertEqual(batch.state, "exported")
        batch.action_reopen()
        # a user may not delete a batch (the trail stays)
        with self.assertRaises(AccessError):
            batch.unlink()

    def test_setup_is_for_managers(self):
        env = self.env(user=self.user)
        with self.assertRaises(AccessError):
            env["dma.fr.source"].create({"name": "x", "mode": "live"})
        with self.assertRaises(AccessError):
            env["dma.fr.source"].browse(self.source.id).action_refresh()
        with self.assertRaises(AccessError):
            env["dma.fr.source"].browse(self.source.id).read(["db_password"])
        with self.assertRaises(AccessError):
            env["dma.fr.template"].browse(self.env.ref("dma_field_reports.template_eore").id).write({"name": "x"})
        # the manager may
        menv = self.env(user=self.manager)
        self.assertEqual(menv["dma.fr.source"].browse(self.source.id).read(["db_password"])[0]["db_password"], "secret")
        menv["dma.fr.template"].browse(self.env.ref("dma_field_reports.template_eore").id).write({"sequence": 11})

    def test_other_staff_see_nothing(self):
        env = self.env(user=self.outsider)
        with self.assertRaises(AccessError):
            env["dma.fr.batch"].search([])
        menu = self.env.ref("dma_field_reports.menu_dma_fr_root")
        self.assertNotIn(menu.id, env["ir.ui.menu"]._visible_menu_ids())
