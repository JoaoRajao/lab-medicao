from datetime import date


def consolidate_batches(batches, today):
  today_date = date.fromisoformat(today)
  aggregated = {}

  for batch in batches:
    if date.fromisoformat(batch['expires_at']) < today_date:
      continue

    sku = batch['sku']
    quantity = batch['quantity']
    expires_at = batch['expires_at']
    priority = batch['priority']

    if sku not in aggregated:
      aggregated[sku] = {
          'sku': sku,
          'quantity': quantity,
          'next_expiration': expires_at,
          'max_priority': priority,
      }
    else:
      aggregated[sku]['quantity'] += quantity
      if expires_at < aggregated[sku]['next_expiration']:
        aggregated[sku]['next_expiration'] = expires_at
      if priority > aggregated[sku]['max_priority']:
        aggregated[sku]['max_priority'] = priority

  result = list(aggregated.values())

  result.sort(key=lambda x: (x['sku'], x['next_expiration']))

  return result
