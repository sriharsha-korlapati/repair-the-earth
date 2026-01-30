import yaml

def calculate_units_from_bill(bill_amount, tariff_file):
    with open(tariff_file, "r") as f:
        tariff = yaml.safe_load(f)

    slabs = tariff["household_tariff"]["slabs"]

    remaining_amount = bill_amount
    total_units = 0
    previous_limit = 0

    for slab in slabs:
        if "upto_units" in slab:
            slab_units = slab["upto_units"] - previous_limit
            slab_cost = slab_units * slab["rate_per_unit"]

            if remaining_amount >= slab_cost:
                total_units += slab_units
                remaining_amount -= slab_cost
                previous_limit = slab["upto_units"]
            else:
                total_units += remaining_amount / slab["rate_per_unit"]
                return round(total_units, 2)
        else:
            total_units += remaining_amount / slab["rate_per_unit"]
            return round(total_units, 2)

    return round(total_units, 2)