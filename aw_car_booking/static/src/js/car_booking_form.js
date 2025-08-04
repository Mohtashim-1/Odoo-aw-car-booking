/** @odoo-module **/

import { Component, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CarBookingForm extends Component {
    setup() {
        this.state = useState({
            bookingType: "",
            driverInfo: "",
            customerType: "",
            customerId: "",
            carId: "",
            startDate: "",
            endDate: "",
            cars: [],
            customers: [],
        });

        this.rpc = useService("rpc");

        this.loadCars();
        this.loadCustomers();
    }

    // Load cars data from fleet.vehicle model
    async loadCars() {
        try {
            const cars = await this.rpc({
                model: "fleet.vehicle",
                method: "search_read",
                args: [[], ["id", "name"]],
            });
            this.state.cars = cars;
        } catch (error) {
            console.error("Error loading cars:", error);
        }
    }

    // Load customer data from res.partner model
    async loadCustomers() {
        try {
            const customers = await this.rpc({
                model: "res.partner",
                method: "search_read",
                args: [[], ["id", "name"]],
            });
            this.state.customers = customers;
        } catch (error) {
            console.error("Error loading customers:", error);
        }
    }

    // Handle form submission
    async submitForm() {
        try {
            const response = await fetch('/car_booking/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    booking_type: this.state.bookingType,
                    customer_type: this.state.customerType,
                    customer_id: this.state.customerId,
                    car_id: this.state.carId,
                    start_date: this.state.startDate,
                    end_date: this.state.endDate,
                    driver_info: this.state.driverInfo,
                }),
            });

            const result = await response.json();
            if (result.status === 'success') {
                alert(result.message);
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error("Error submitting the booking:", error);
        }
    }

    static template = "car_booking.Form";
}

registry.category("actions").add("car_booking.form_action", CarBookingForm);
