from datetime import date


def calculate_invoice(invoice, paid_at):
  amount = invoice['amount']
  due_at = invoice['due_at']
  early_discount_pct = invoice.get('early_discount_pct', 0.0)
  late_fee_pct = invoice.get('late_fee_pct', 0.0)

  paid_date = date.fromisoformat(paid_at)
  due_date = date.fromisoformat(due_at)

  days_delta = (paid_date - due_date).days

  if paid_date < due_date:
    status = 'early'
    final_amount = amount * (1 - early_discount_pct / 100)
  elif paid_date == due_date:
    status = 'on_time'
    final_amount = amount
  else:
    status = 'late'
    final_amount = amount * (1 + late_fee_pct / 100)

  final_amount = round(final_amount, 2)

  return {
      'final_amount': final_amount,
      'status': status,
      'days_delta': days_delta,
  }
