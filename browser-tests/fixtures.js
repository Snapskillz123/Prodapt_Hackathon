// Offline fixture only: never imported by production UI code.
import fs from "node:fs";
const sample = JSON.parse(
  fs.readFileSync("examples/tripai/valid-result.json", "utf8"),
);
const trip = sample.trip;
const amounts = Object.fromEntries(
  sample.budget.breakdown.map((row) => [row.category, row.amount]),
);
export const plan = {
  profile: {
    destination: trip.preferences.destination,
    startDate: trip.preferences.startDate,
    days: trip.days.length,
    travelers: trip.preferences.travellers,
    budget: trip.preferences.totalBudget,
    currency: "INR",
    interests: trip.preferences.interests.join(", "),
    style: trip.preferences.style,
    requirements: trip.preferences.requirements,
  },
  summary: "Dummy itinerary for browser testing only.",
  days: trip.days.map((day, index) => ({
    day: index + 1,
    title: day.title,
    activities: day.activities.map((activity) => ({
      ...activity,
      place: {
        id: activity.id,
        name: activity.title,
        address: activity.location,
        lat: 26.92,
        lng: 75.82,
      },
    })),
  })),
  budget: {
    accommodation: amounts.accommodation,
    food: amounts.food,
    localTransport: amounts.transport,
    activities: amounts.activities,
    contingency: amounts.miscellaneous,
    total: sample.budget.estimatedSpend,
    remaining: sample.budget.remaining,
  },
  packing: trip.packing.flatMap((category) =>
    category.items.map((item) => item.name),
  ),
  weather: [],
  warnings: sample.warnings,
  notes: sample.notes,
};
