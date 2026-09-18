def prioritize_tickets(tickets):
  severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

  def sort_key(ticket):
    is_breached = 0 if ticket['minutes_to_sla'] < 0 else 1

    severity_val = severity_order.get(ticket['severity'], 4)

    minutes = ticket['minutes_to_sla']

    seq = ticket['created_seq']

    return (is_breached, severity_val, minutes, seq)

  sorted_tickets = sorted(tickets, key=sort_key)
  return [t['id'] for t in sorted_tickets]
