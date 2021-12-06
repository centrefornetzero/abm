import datetime
import random

import pytest

from simulation.agents import Household
from simulation.constants import (
    BOILERS,
    HEAT_PUMPS,
    BuiltForm,
    ConstructionYearBand,
    Epc,
    HeatingSystem,
    OccupantType,
    PropertyType,
)
from simulation.costs import (
    get_heating_fuel_costs_net_present_value,
    get_unit_and_install_costs,
)
from simulation.model import CnzAgentBasedModel


def household_factory(**agent_attributes):
    default_values = {
        "location": "Test Location",
        "property_value": 264_000,
        "floor_area_sqm": 82,
        "off_gas_grid": False,
        "construction_year_band": ConstructionYearBand.BUILT_1919_1944,
        "property_type": PropertyType.HOUSE,
        "built_form": BuiltForm.MID_TERRACE,
        "heating_system": HeatingSystem.BOILER_GAS,
        "heating_system_install_date": datetime.date(2021, 1, 1),
        "epc": Epc.D,
        "potential_epc": Epc.C,
        "occupant_type": OccupantType.OWNER_OCCUPIER,
        "is_solid_wall": False,
        "walls_energy_efficiency": 3,
        "windows_energy_efficiency": 3,
        "roof_energy_efficiency": 3,
        "is_heat_pump_suitable_archetype": True,
        "is_heat_pump_aware": True,
    }
    return Household(**{**default_values, **agent_attributes})


def model_factory(**model_attributes):
    default_values = {
        "start_datetime": datetime.datetime.now(),
        "step_interval": datetime.timedelta(minutes=1440),
        "annual_renovation_rate": 0.05,
    }
    return CnzAgentBasedModel(**{**default_values, **model_attributes})


class TestCosts:
    @pytest.mark.parametrize("heating_system", set(HeatingSystem))
    def test_cost_of_any_heating_system_is_cheaper_if_already_installed(
        self, heating_system
    ) -> None:
        household_sticking_same_system = household_factory(
            heating_system=heating_system
        )

        alternative_system = random.choice(list(set(HeatingSystem) - {heating_system}))
        household_switching_system = household_factory(
            heating_system=alternative_system
        )

        assert get_unit_and_install_costs(
            household_sticking_same_system, heating_system
        ) < get_unit_and_install_costs(household_switching_system, heating_system)

    @pytest.mark.parametrize("heat_pump", HEAT_PUMPS)
    def test_cost_of_heat_pump_increases_with_kw_capacity_required(
        self,
        heat_pump,
    ) -> None:

        household = household_factory(
            floor_area_sqm=random.randint(20, 200), heating_system=heat_pump
        )
        larger_household = household_factory(
            floor_area_sqm=household.floor_area_sqm * 1.2,
            heating_system=heat_pump,
        )

        assert household.compute_heat_pump_capacity_kw(
            heat_pump
        ) <= larger_household.compute_heat_pump_capacity_kw(heat_pump)
        assert get_unit_and_install_costs(
            household, heat_pump
        ) <= get_unit_and_install_costs(larger_household, heat_pump)

    @pytest.mark.parametrize("boiler", BOILERS)
    def test_cost_of_boiler_increases_with_property_size(
        self,
        boiler,
    ) -> None:
        household = household_factory(
            floor_area_sqm=random.randint(20, 200), heating_system=boiler
        )
        larger_household = household_factory(
            floor_area_sqm=household.floor_area_sqm * 1.5, heating_system=boiler
        )

        assert get_unit_and_install_costs(
            household, boiler
        ) <= get_unit_and_install_costs(larger_household, boiler)

    @pytest.mark.parametrize("heating_system", set(HeatingSystem))
    def test_fuel_bills_net_present_value_decreases_as_discount_rate_increases(
        self,
        heating_system,
    ) -> None:

        num_look_ahead_years = random.randint(2, 10)
        household = household_factory(property_value=random.randint(50_000, 300_000))
        wealthier_household = household_factory(
            property_value=household.property_value * 1.1
        )

        assert household.discount_rate > wealthier_household.discount_rate

        assert get_heating_fuel_costs_net_present_value(
            household, heating_system, num_look_ahead_years
        ) < get_heating_fuel_costs_net_present_value(
            wealthier_household, heating_system, num_look_ahead_years
        )
