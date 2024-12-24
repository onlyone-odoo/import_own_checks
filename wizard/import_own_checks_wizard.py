# import_own_checks/wizard/import_own_checks_wizard.py
import io
import base64
import logging
from datetime import date
from odoo import api, fields, models

_logger = logging.getLogger(__name__)  # Logger para depurar

try:
    import openpyxl
except ImportError:
    _logger.warning("openpyxl not installed.")


class ImportOwnChecksWizard(models.TransientModel):
    _name = "import.own.checks.wizard"
    _description = "Wizard to import Own checks from Excel"

    default_date = fields.Date(string="Default Payment Date")
    file_data = fields.Binary(string="File (Excel)")
    file_name = fields.Char(string="File Name")

    def action_import(self):
        if not self.file_data:
            return

        today_date = date.today()
        file_stream = io.BytesIO(base64.b64decode(self.file_data))

        wb = openpyxl.load_workbook(
            file_stream,
            data_only=True,
            read_only=True,
        )
        sheet = wb.active

        row_index = 0
        for row in sheet.iter_rows(values_only=True):
            row_index += 1
            if row_index == 1:  # Saltear el encabezado
                continue

            partner_name = row[0]
            amount = row[1]
            currency_code = row[2]
            ref = row[3]
            check_number = row[4]
            check_payment_date = row[5]
            journal_id_name = row[6]

            _logger.info(f"Processing row {row_index}: {row}")

            journal_id = False
            if journal_id_name:
                journal = self.env["account.journal"].search(
                    [("name", "=", journal_id_name)], limit=1
                )
                if journal:
                    # Verificar si el diario tiene el método de pago "Cheques"
                    has_cheque_method = any(
                        line.payment_method_id.name == "Cheques"
                        for line in journal.outbound_payment_method_line_ids
                    )
                    if has_cheque_method:
                        journal_id = journal.id
                        _logger.info(
                            f"Journal '{journal_id_name}' has cheque payment method."
                        )
                    else:
                        _logger.warning(
                            f"Journal '{journal_id_name}' does not have the cheque payment method."
                        )
                        continue  # Salta a la siguiente línea del Excel
                else:
                    _logger.warning(f"Journal '{journal_id_name}' not found.")
                    continue  # Salta a la siguiente línea del Excel

            partner_id = False
            if partner_name:
                partner = self.env["res.partner"].search(
                    [("name", "=", partner_name)], limit=1
                )
                if partner:
                    _logger.info(f"Found partner '{partner_name}' with ID {partner.id}")
                    partner_id = partner.id
                else:
                    # Crear un nuevo partner si no se encuentra
                    new_partner = self.env["res.partner"].create(
                        {
                            "name": partner_name,
                        }
                    )
                    _logger.info(
                        f"Created new partner '{partner_name}' with ID {new_partner.id}"
                    )
                    partner_id = new_partner.id

            currency_id = self.env.company.currency_id.id
            if currency_code:
                currency = self.env["res.currency"].search(
                    [("name", "=", currency_code)], limit=1
                )
                if currency:
                    _logger.info(
                        f"Found currency '{currency_code}' with ID {currency.id}"
                    )
                    currency_id = currency.id
                else:
                    _logger.warning(
                        f"Currency '{currency_code}' not found, defaulting to company currency"
                    )

            if not amount:
                _logger.warning(f"Skipping row {row_index} due to missing amount")
                continue

            payment_date = (self.default_date or today_date).isoformat()
            if check_payment_date:
                payment_date = check_payment_date.isoformat()

            receiptbook = self.env["account.payment.receiptbook"].search(
                [
                    ("company_id", "=", self.env.company.id),
                    ("partner_type", "=", "supplier"),
                ],
                limit=1,
            )
            _logger.info(
                f"Using receiptbook ID {receiptbook.id if receiptbook else 'None'}"
            )

            payment_group_vals = {
                "partner_id": partner_id,
                "company_id": self.env.company.id,
                "payment_date": today_date,  # O usa payment_date si deseas
                "receiptbook_id": receiptbook.id if receiptbook else False,
                "communication": ref if ref else False,
                "partner_type": "supplier",
            }
            _logger.info(f"Creating payment group with values: {payment_group_vals}")
            payment_group = self.env["account.payment.group"].create(payment_group_vals)

            payment_vals = {
                "payment_group_id": payment_group.id,
                "partner_id": partner_id,
                "amount": amount,
                "currency_id": currency_id,
                "date": today_date,  # O usa payment_date si deseas
                "journal_id": journal_id,
                "payment_type": "outbound",
                "ref": ref if ref else False,
                "l10n_latam_check_number": check_number,
                "l10n_latam_check_payment_date": payment_date,
            }

            _logger.info(f"Creating payment with values: {payment_vals}")
            payment = self.env["account.payment"].create(payment_vals)
            # validar el payment_group
            payment_group.post()
            # Revertir el asiento contable asociado
            self._revert_payment_move(payment)
        return

    def _revert_payment_move(self, payment):
        """Reversión automática del asiento contable del pago."""
        if not payment.move_id:
            _logger.warning(f"No journal entry found for payment ID {payment.id}")
            return

        _logger.info(f"Reversing journal entry for payment ID {payment.id}")

        # Llama a la acción de reversión
        reversal_wizard = self.env["account.move.reversal"].create(
            {
                "move_ids": [
                    (6, 0, [payment.move_id.id])
                ],  # Relación con el asiento contable
                "date": fields.Date.context_today(self),
                "journal_id": payment.journal_id.id,
                "reason": "Reversal of OWN check import",
            }
        )

        reversal_wizard.reverse_moves()
        _logger.info(f"Reversed journal entry for payment ID {payment.id}")


# si todo sale bien esto deberia dejar cheques sin asientos contables
