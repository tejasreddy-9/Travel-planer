from fastapi import APIRouter, HTTPException
from models import PlanRequest, PlanResponse, SuggestionRequest, GroupTripRequest, BookingRequest
from database import plans_collection, feedback_collection
from llm_client import generate_itinerary
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Travel Planner"])

class SuggestionRequest(BaseModel):
    query: str


def _to_response(doc) -> PlanResponse:
    return PlanResponse(
        id=doc["user_id"],
        destination=doc["destination"],
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        preferences=doc.get("preferences"),
        travelers=doc.get("travelers"),
        plan_text=doc["plan_text"],
        created_at=str(doc["created_at"])
    )

# --------------------
# Available Locations Endpoint
# --------------------
@router.get("/locations")
async def get_locations():
    """
    Returns all available locations where user can plan trips.
    Includes Indian Capitals, States, and World Cities.
    """
    return {
        "indian_capitals": list(INDIA_CAPITALS.keys()),
        "indian_states": list(INDIA_STATES.keys()),
        "world_cities": list(WORLD_TOURISM.keys())
    }

#---------------------------------------------------------------------------------------------------------------
# --------------------
# Create Plan with Full Journey + Budget Split
# --------------------
@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    try:
        # Check if user_id already exists
        existing = await plans_collection.find_one({"user_id": req.user_id})
        if existing:
            raise HTTPException(status_code=400, detail="User ID already exists. Please choose a different ID.")
        
        if not req.start_point:
            raise HTTPException(status_code=400, detail="Start point (home city) is required")

        # Prepare trip duration
        dates = f"{req.start_date or 'NA'} to {req.end_date or 'NA'}"

        # ---------------------------
        # Generate AI itinerary (visiting places only)
        # ---------------------------
        core_itinerary = await generate_itinerary(
            req.destination, dates, req.travelers or 1, req.preferences or ""
        )

        # ---------------------------
        # Find transport (mock logic for demo)
        # ---------------------------
        transport = f"Train/Flight/Bus from {req.start_point} → {req.destination}"

        # ---------------------------
        # Suggest hotels & restaurants
        # ---------------------------
        hotels = []
        restaurants = []
        tourism_spots = []

        if req.destination.lower() in INDIA_CAPITALS:
            hotels = INDIA_CAPITALS[req.destination.lower()]["hotels"]
            restaurants = INDIA_CAPITALS[req.destination.lower()]["restaurants"]
            tourism_spots = INDIA_CAPITALS[req.destination.lower()]["tourism"]

        elif req.destination.lower() in INDIA_STATES:
            hotels = INDIA_STATES[req.destination.lower()]["hotels"]
            restaurants = INDIA_STATES[req.destination.lower()]["restaurants"]
            tourism_spots = INDIA_STATES[req.destination.lower()]["tourism"]

        elif req.destination.lower() in WORLD_TOURISM:
            hotels = WORLD_TOURISM[req.destination.lower()]["hotels"]
            restaurants = WORLD_TOURISM[req.destination.lower()]["restaurants"]
            tourism_spots = WORLD_TOURISM[req.destination.lower()]["tourism"]

        # ---------------------------
        # Budget calculation
        # ---------------------------
        total_budget = req.budget or 0
        members = req.num_of_members or 1
        per_person_budget = total_budget // members if members > 0 else total_budget

        # ---------------------------
        # Build final trip plan
        # ---------------------------
        plan_text = f"""
        🏁 Starting Point: {req.start_point}

        🚉 Travel: {transport}

        🏨 Stay: Recommended Hotels → {hotels}

        🍴 Food: Suggested Restaurants → {restaurants}

        🏝 Tourism: Must Visit Places → {tourism_spots}

        📅 Itinerary Plan:
        {core_itinerary}

        💰 Budget:
        Total Budget = ₹{total_budget}
        Members = {members}
        Per Person = ₹{per_person_budget}

        🔄 Return: {req.destination} → {req.start_point}
        """

        # ---------------------------
        # Save to DB
        # ---------------------------
        doc = {
            "user_id": req.user_id,
            "start_point": req.start_point,
            "destination": req.destination,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "preferences": req.preferences,
            "travelers": req.travelers,
            "budget": total_budget,
            "num_of_members": members,
            "plan_text": plan_text,
            "created_at": datetime.utcnow()
        }

        res = await plans_collection.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _to_response(doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------------------------------------------------------------------------------


# --------------------
# Get Plan by user_id (no ObjectId)
# --------------------
@router.get("/plan/{user_id}", response_model=PlanResponse)
async def get_plan(user_id: str):
    doc = await plans_collection.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Plan not found for this user_id")
    return _to_response(doc)



#------------------------------------------------------------------------------------------------------------
# --------------------
# Suggestions with Hotels
# --------------------

INDIA_CAPITALS = {
    "delhi": {
        "tourism": ["India Gate", "Red Fort", "Qutub Minar", "Lotus Temple"],
        "hotels": {
            "low_budget_hotels": ["Zostel Delhi", "Hotel Hari Piorko", "budget: ₹1,200 – ₹2,800 per day"],
            "high_budget_hotels": ["The Oberoi New Delhi", "Taj Palace", "budget: ₹12,000 – ₹45,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Karim's",
                "menu": {
                    "Chicken Biryani": "₹350",
                    "Mutton Korma": "₹420",
                    "Butter Naan (2)": "₹60",
                    "Raita": "₹40"
                }
            },
            "restaurant_2": {
                "name": "Sagar Ratna",
                "menu": {
                    "Masala Dosa": "₹180",
                    "Idli Sambar (2)": "₹120",
                    "Medu Vada": "₹80",
                    "Filter Coffee": "₹70"
                }
            }
        }
    },
    "mumbai": {
        "tourism": ["Gateway of India", "Marine Drive", "Elephanta Caves", "Juhu Beach"],
        "hotels": {
            "low_budget_hotels": ["YMCA Mumbai", "Hotel City Palace", "budget: ₹1,000 – ₹2,500 per day"],
            "high_budget_hotels": ["The Taj Mahal Palace", "Trident Nariman Point", "budget: ₹15,000 – ₹55,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Bademiya (Colaba)",
                "menu": {
                    "Seekh Kebab": "₹220",
                    "Chicken Tikka Roll": "₹180",
                    "Butter Roti": "₹40",
                    "Masala Chai": "₹40"
                }
            },
            "restaurant_2": {
                "name": "Swati Snacks",
                "menu": {
                    "Pav Bhaji (plate)": "₹150",
                    "Handvo Slice": "₹90",
                    "Khaman Dhokla": "₹80",
                    "Gulab Jamun (2)": "₹70"
                }
            }
        }
    },
    "chennai": {
        "tourism": ["Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "Guindy National Park"],
        "hotels": {
            "low_budget_hotels": ["Olive Residency", "Siesta Star T. Nagar", "budget: ₹1,300 – ₹2,700 per day"],
            "high_budget_hotels": ["ITC Grand Chola", "The Leela Palace", "budget: ₹10,000 – ₹40,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Murugan Idli Shop",
                "menu": {
                    "Idli (2)": "₹60",
                    "Sambar": "₹40",
                    "Pongal": "₹120",
                    "Filter Coffee": "₹50"
                }
            },
            "restaurant_2": {
                "name": "Anjappar Chettinad",
                "menu": {
                    "Chicken Chettinad (plate)": "₹220",
                    "Mutton Kola Urundai (2)": "₹180",
                    "Parotta (2)": "₹80",
                    "Curd Rice": "₹90"
                }
            }
        }
    },
    "kolkata": {
        "tourism": ["Victoria Memorial", "Howrah Bridge", "Dakshineswar Kali Temple", "Science City"],
        "hotels": {
            "low_budget_hotels": ["Backpackers Hostel", "Hotel Airways", "budget: ₹900 – ₹2,200 per day"],
            "high_budget_hotels": ["The Oberoi Grand", "ITC Royal Bengal", "budget: ₹13,000 – ₹48,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Peter Cat",
                "menu": {
                    "Chelo Kebabs": "₹420",
                    "Mutton Curry (plate)": "₹350",
                    "Kebabs (assorted)": "₹300",
                    "Lassi": "₹120"
                }
            },
            "restaurant_2": {
                "name": "Bhojohori Manna",
                "menu": {
                    "Kosha Mangsho": "₹280",
                    "Bhetki Paturi": "₹320",
                    "Shorshe Ilish (seasonal)": "₹400",
                    "Mishti Doi": "₹90"
                }
            }
        }
    },
    "hyderabad": {
        "tourism": ["Charminar", "Golconda Fort", "Ramoji Film City", "Hussain Sagar Lake"],
        "hotels": {
            "low_budget_hotels": ["Zostel Hyderabad", "Hotel City Park", "budget: ₹1,400 – ₹2,900 per day"],
            "high_budget_hotels": ["Taj Falaknuma Palace", "Park Hyatt Hyderabad", "budget: ₹14,000 – ₹60,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Paradise Biryani",
                "menu": {
                    "Chicken Biryani (plate)": "₹300",
                    "Mutton Biryani (plate)": "₹380",
                    "Mirchi Ka Salan (side)": "₹90",
                    "Double Ka Meetha": "₹120"
                }
            },
            "restaurant_2": {
                "name": "Cafe Niloufer",
                "menu": {
                    "Osmania Biscuit + Tea": "₹80",
                    "Haleem (seasonal)": "₹220",
                    "Chicken Fry": "₹250",
                    "Irani Chai": "₹50"
                }
            }
        }
    },
    "bengaluru": {
        "tourism": ["Cubbon Park", "Lalbagh Botanical Garden", "Bangalore Palace", "Vidhana Soudha"],
        "hotels": {
            "low_budget_hotels": ["Backpacker Panda", "Hotel Tap Gold Crest", "budget: ₹1,200 – ₹2,600 per day"],
            "high_budget_hotels": ["The Leela Palace", "Taj West End", "budget: ₹12,500 – ₹42,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Vidyarthi Bhavan",
                "menu": {
                    "Masala Dosa (single)": "₹120",
                    "Idli (2)": "₹60",
                    "Filter Coffee": "₹50",
                    "Benne Dosa (butter dosa)": "₹160"
                }
            },
            "restaurant_2": {
                "name": "MTR (Mavalli Tiffin Rooms)",
                "menu": {
                    "Rava Idli": "₹95",
                    "Kesari Bath": "₹80",
                    "Bisi Bele Bath": "₹140",
                    "Sambar": "₹40"
                }
            }
        }
    },
    "lucknow": {
        "tourism": ["Bara Imambara", "Rumi Darwaza", "Hazratganj", "Ambedkar Memorial Park"],
        "hotels": {
            "low_budget_hotels": ["Hotel Deep Palace", "Hostel by Roadhouse", "budget: ₹1,000 – ₹2,400 per day"],
            "high_budget_hotels": ["Taj Mahal Lucknow", "Hyatt Regency Lucknow", "budget: ₹11,000 – ₹39,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Tunday Kababi",
                "menu": {
                    "Galouti Kebab (piece)": "₹70",
                    "Sheermal (piece)": "₹40",
                    "Kebab Platter": "₹320",
                    "Kahwa/Chai": "₹50"
                }
            },
            "restaurant_2": {
                "name": "Dastarkhwan",
                "menu": {
                    "Nihari (plate)": "₹260",
                    "Biryani (plate)": "₹220",
                    "Kulfi Falooda": "₹120",
                    "Rumali Roti (2)": "₹60"
                }
            }
        }
    }
}


INDIA_STATES = {
    "rajasthan": {
        "tourism": ["Jaipur (Pink City)", "Udaipur", "Jaisalmer Fort", "Mount Abu"],
        "hotels": {
            "low_budget_hotels": ["Zostel Jaipur", "Bunkyard Hostel Udaipur", "budget: ₹1,000 – ₹2,800 per day"],
            "high_budget_hotels": ["Rambagh Palace Jaipur", "The Leela Palace Udaipur", "budget: ₹18,000 – ₹65,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Laxmi Mishthan Bhandar (LMB)",
                "menu": {
                    "Dal Baati Churma": "₹250",
                    "Pyaaz Kachori": "₹80",
                    "Ghewar (slice)": "₹150",
                    "Rajasthani Thali": "₹420"
                }
            },
            "restaurant_2": {
                "name": "1135 AD (Jaipur)",
                "menu": {
                    "Laal Maas (plate)": "₹450",
                    "Ker Sangri": "₹280",
                    "Bajra Roti (2)": "₹100",
                    "Mawa Kachori": "₹120"
                }
            }
        }
    },
    "kerala": {
        "tourism": ["Alleppey Backwaters", "Munnar", "Kochi", "Kovalam Beach"],
        "hotels": {
            "low_budget_hotels": ["Green View Munnar", "Vedanta Wake Up Alleppey", "budget: ₹1,100 – ₹2,500 per day"],
            "high_budget_hotels": ["Kumarakom Lake Resort", "Le Meridien Kochi", "budget: ₹12,000 – ₹38,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Dhe Puttu (Kochi)",
                "menu": {
                    "Chicken Puttu": "₹220",
                    "Fish Curry": "₹280",
                    "Appam (2)": "₹80",
                    "Payasam": "₹120"
                }
            },
            "restaurant_2": {
                "name": "Ariya Bhavan (Thiruvananthapuram)",
                "menu": {
                    "Vegetarian Thali": "₹180",
                    "Idiyappam with Curry": "₹150",
                    "Banana Chips (packet)": "₹90",
                    "Filter Coffee": "₹70"
                }
            }
        }
    },
    "goa": {
        "tourism": ["Baga Beach", "Dudhsagar Waterfalls", "Fort Aguada", "Anjuna Beach"],
        "hotels": {
            "low_budget_hotels": ["The Hosteller Goa", "Jungle by the Hostel Crowd", "budget: ₹900 – ₹2,200 per day"],
            "high_budget_hotels": ["Taj Exotica Goa", "W Goa", "budget: ₹14,500 – ₹52,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Mum’s Kitchen",
                "menu": {
                    "Goan Fish Curry": "₹300",
                    "Prawn Balchao": "₹350",
                    "Poi Bread (2)": "₹60",
                    "Bebinca (slice)": "₹150"
                }
            },
            "restaurant_2": {
                "name": "Vinayak Family Restaurant",
                "menu": {
                    "Chicken Xacuti": "₹280",
                    "Fish Thali": "₹250",
                    "Feni (local drink)": "₹180",
                    "Sol Kadhi": "₹90"
                }
            }
        }
    },
    "uttarakhand": {
        "tourism": ["Rishikesh", "Haridwar", "Nainital", "Auli"],
        "hotels": {
            "low_budget_hotels": ["Hostel Cozy Beds Rishikesh", "Hotel Lake View Nainital", "budget: ₹1,000 – ₹2,400 per day"],
            "high_budget_hotels": ["The Naini Retreat", "JW Marriott Mussoorie", "budget: ₹13,000 – ₹47,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Chotiwala (Rishikesh)",
                "menu": {
                    "North Indian Thali": "₹220",
                    "Paneer Butter Masala": "₹200",
                    "Tandoori Roti (2)": "₹50",
                    "Sweet Lassi": "₹90"
                }
            },
            "restaurant_2": {
                "name": "Sakley’s Restaurant (Nainital)",
                "menu": {
                    "Veg Pizza": "₹320",
                    "Pasta Alfredo": "₹280",
                    "Brownie with Ice Cream": "₹150",
                    "Hot Chocolate": "₹120"
                }
            }
        }
    },
    "tamil nadu": {
        "tourism": ["Ooty", "Kodaikanal", "Madurai Meenakshi Temple", "Mahabalipuram"],
        "hotels": {
            "low_budget_hotels": ["Backpackers Hive Chennai", "Hotel Tamil Nadu Ooty", "budget: ₹1,200 – ₹2,700 per day"],
            "high_budget_hotels": ["Taj Coromandel Chennai", "Radisson Blu Resort Temple Bay", "budget: ₹12,000 – ₹41,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Murugan Idli (Madurai)",
                "menu": {
                    "Idli (2)": "₹60",
                    "Jigarthanda (drink)": "₹80",
                    "Uthappam": "₹120",
                    "Filter Coffee": "₹50"
                }
            },
            "restaurant_2": {
                "name": "Hotel Saravana Bhavan",
                "menu": {
                    "Mini Tiffin": "₹150",
                    "Onion Rava Dosa": "₹130",
                    "Curd Rice": "₹100",
                    "Kesari Halwa": "₹70"
                }
            }
        }
    },
    "karnataka": {
        "tourism": ["Hampi", "Coorg", "Mysore Palace", "Jog Falls"],
        "hotels": {
            "low_budget_hotels": ["Zostel Coorg", "Hotel Mayura Hampi", "budget: ₹1,000 – ₹2,300 per day"],
            "high_budget_hotels": ["The Tamara Coorg", "Radisson Blu Plaza Mysore", "budget: ₹11,500 – ₹36,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "R R R (Mysuru)",
                "menu": {
                    "Mysore Meals": "₹220",
                    "Bisi Bele Bath": "₹140",
                    "Curd Rice": "₹90",
                    "Payasam": "₹100"
                }
            },
            "restaurant_2": {
                "name": "Coorg Cuisine",
                "menu": {
                    "Pandi Curry (Pork Curry)": "₹350",
                    "Kadambuttu (Rice Balls)": "₹120",
                    "Akki Roti (2)": "₹100",
                    "Coorgi Coffee": "₹80"
                }
            }
        }
    },
    "punjab": {
        "tourism": ["Golden Temple Amritsar", "Jallianwala Bagh", "Wagah Border", "Anandpur Sahib"],
        "hotels": {
            "low_budget_hotels": ["Hotel City Park Amritsar", "Backpacker’s Nest", "budget: ₹1,100 – ₹2,600 per day"],
            "high_budget_hotels": ["Hyatt Regency Amritsar", "Ramada Amritsar", "budget: ₹10,000 – ₹34,000 per day"]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Kesar Da Dhaba",
                "menu": {
                    "Dal Makhani": "₹220",
                    "Paneer Butter Masala": "₹260",
                    "Tandoori Roti (2)": "₹60",
                    "Phirni": "₹90"
                }
            },
            "restaurant_2": {
                "name": "Bharawan Da Dhaba",
                "menu": {
                    "Amritsari Kulcha": "₹120",
                    "Chole (plate)": "₹150",
                    "Lassi (glass)": "₹80",
                    "Rajma Chawal": "₹200"
                }
            }
        }
    }
}


WORLD_TOURISM = {
    "paris": {
        "tourism": ["Eiffel Tower", "Louvre Museum", "Notre Dame Cathedral", "Seine River Cruise"],
        "hotels": {
            "low_budget_hotels": [
                "Generator Paris Hostel",
                "St. Christopher’s Inn",
                "Hotel ibis Budget Paris",
                "Le Regent Montmartre Hostel",
                "budget: ₹3,600 – ₹10,800 per day"
            ],
            "high_budget_hotels": [
                "Hotel Plaza Athénée",
                "The Ritz Paris",
                "budget: ₹54,000 – ₹1,80,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Le Jules Verne",
                "menu": {
                    "Foie Gras": "₹7,200",
                    "Duck Confit": "₹10,800",
                    "Crème Brûlée": "₹4,050"
                }
            },
            "restaurant_2": {
                "name": "Le Relais de l’Entrecôte",
                "menu": {
                    "Steak Frites": "₹3,600",
                    "French Onion Soup": "₹2,250",
                    "Tarte Tatin": "₹1,800"
                }
            },
            "restaurant_3": {
                "name": "Bouillon Pigalle",
                "menu": {
                    "Escargot": "₹2,700",
                    "Beef Bourguignon": "₹5,400",
                    "Chocolate Mousse": "₹1,800"
                }
            },
            "restaurant_4": {
                "name": "Chez Janou",
                "menu": {
                    "Ratatouille": "₹2,250",
                    "Seafood Pasta": "₹6,300",
                    "Crème Caramel": "₹1,800"
                }
            }
        }
    },

    "new york": {
        "tourism": ["Statue of Liberty", "Times Square", "Central Park", "Empire State Building"],
        "hotels": {
            "low_budget_hotels": [
                "HI NYC Hostel",
                "Pod 51 Hotel",
                "Chelsea International Hostel",
                "Q4 Hotel Queens",
                "budget: ₹5,800 – ₹12,450 per day"
            ],
            "high_budget_hotels": [
                "The Plaza Hotel",
                "The St. Regis New York",
                "budget: ₹58,000 – ₹1,66,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Katz’s Delicatessen",
                "menu": {
                    "Pastrami Sandwich": "₹2,075",
                    "Hot Dog": "₹1,000",
                    "Cheesecake": "₹1,250"
                }
            },
            "restaurant_2": {
                "name": "Joe’s Pizza",
                "menu": {
                    "New York Slice": "₹415",
                    "Garlic Knots": "₹660",
                    "Soda": "₹250"
                }
            },
            "restaurant_3": {
                "name": "Shake Shack",
                "menu": {
                    "ShackBurger": "₹660",
                    "Crinkle Fries": "₹330",
                    "Milkshake": "₹500"
                }
            },
            "restaurant_4": {
                "name": "Gray’s Papaya",
                "menu": {
                    "Hot Dog Combo": "₹830",
                    "Papaya Juice": "₹330",
                    "Cheese Dog": "₹1,000"
                }
            }
        }
    },

    "london": {
        "tourism": ["Big Ben", "London Eye", "Tower of London", "Buckingham Palace"],
        "hotels": {
            "low_budget_hotels": [
                "Generator London Hostel",
                "Clink78 Hostel",
                "Astor Museum Hostel",
                "YHA London Central",
                "budget: ₹4,000 – ₹12,000 per day"
            ],
            "high_budget_hotels": [
                "The Savoy",
                "The Ritz London",
                "budget: ₹50,000 – ₹1,50,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Dishoom Covent Garden",
                "menu": {
                    "Chicken Tikka": "₹1,400",
                    "Black Daal": "₹1,200",
                    "Garlic Naan": "₹500"
                }
            },
            "restaurant_2": {
                "name": "The Ivy",
                "menu": {
                    "Fish & Chips": "₹2,000",
                    "Shepherd’s Pie": "₹1,800",
                    "Sticky Toffee Pudding": "₹1,000"
                }
            },
            "restaurant_3": {
                "name": "Pret A Manger",
                "menu": {
                    "Avocado Sandwich": "₹800",
                    "Latte Coffee": "₹400",
                    "Croissant": "₹300"
                }
            },
            "restaurant_4": {
                "name": "Duck & Waffle",
                "menu": {
                    "Duck Confit Waffle": "₹2,500",
                    "Egg Benedict": "₹1,400",
                    "Chocolate Fondant": "₹1,200"
                }
            }
        }
    },

    "dubai": {
        "tourism": ["Burj Khalifa", "Palm Jumeirah", "Dubai Mall", "Desert Safari"],
        "hotels": {
            "low_budget_hotels": [
                "Citymax Hotel Bur Dubai",
                "Premier Inn Dubai",
                "Holiday Inn Express",
                "Rove Downtown",
                "budget: ₹4,600 – ₹11,500 per day"
            ],
            "high_budget_hotels": [
                "Burj Al Arab Jumeirah",
                "Atlantis The Palm",
                "budget: ₹57,500 – ₹2,30,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Al Fanar Restaurant",
                "menu": {
                    "Machboos": "₹1,500",
                    "Luqaimat": "₹920",
                    "Grilled Hammour": "₹2,070"
                }
            },
            "restaurant_2": {
                "name": "Ravi Restaurant",
                "menu": {
                    "Chicken Karahi": "₹1,035",
                    "Mutton Biryani": "₹1,150",
                    "Paratha": "₹230"
                }
            },
            "restaurant_3": {
                "name": "Al Ustad Special Kebab",
                "menu": {
                    "Mutton Kebab": "₹1,500",
                    "Chicken Tikka": "₹1,200",
                    "Rice with Gravy": "₹800"
                }
            },
            "restaurant_4": {
                "name": "Arabian Tea House",
                "menu": {
                    "Hummus": "₹600",
                    "Falafel Plate": "₹1,000",
                    "Shawarma": "₹900"
                }
            }
        }
    },

    "rome": {
        "tourism": ["Colosseum", "Trevi Fountain", "Vatican City", "Pantheon"],
        "hotels": {
            "low_budget_hotels": [
                "The Beehive Hostel",
                "Alessandro Palace Hostel",
                "Freedom Traveller Hostel",
                "Dreaming Rome Hostel",
                "budget: ₹4,500 – ₹10,800 per day"
            ],
            "high_budget_hotels": [
                "Hotel de Russie",
                "Rome Cavalieri, A Waldorf Astoria Hotel",
                "budget: ₹45,000 – ₹1,35,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Trattoria da Enzo",
                "menu": {
                    "Carbonara": "₹1,350",
                    "Cacio e Pepe": "₹1,260",
                    "Tiramisu": "₹720"
                }
            },
            "restaurant_2": {
                "name": "Roscioli",
                "menu": {
                    "Pizza Margherita": "₹1,080",
                    "Prosciutto & Melon": "₹1,620",
                    "Gelato": "₹540"
                }
            },
            "restaurant_3": {
                "name": "Pizzeria La Montecarlo",
                "menu": {
                    "Pizza Diavola": "₹1,440",
                    "Bruschetta": "₹540",
                    "House Wine Glass": "₹720"
                }
            },
            "restaurant_4": {
                "name": "Osteria da Fortunata",
                "menu": {
                    "Fresh Pasta": "₹1,800",
                    "Meatballs": "₹1,260",
                    "Panna Cotta": "₹900"
                }
            }
        }
    },

    "tokyo": {
        "tourism": ["Tokyo Tower", "Shinjuku", "Mount Fuji (day trip)", "Shibuya Crossing"],
        "hotels": {
            "low_budget_hotels": [
                "Khaosan Tokyo Origami",
                "Sakura Hostel Asakusa",
                "K’s House Tokyo",
                "Tokyo Central Youth Hostel",
                "budget: ₹2,400 – ₹5,400 per day"
            ],
            "high_budget_hotels": [
                "Park Hyatt Tokyo",
                "The Ritz-Carlton Tokyo",
                "budget: ₹36,000 – ₹90,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Ichiran Ramen",
                "menu": {
                    "Tonkotsu Ramen": "₹590",
                    "Extra Noodles": "₹120",
                    "Green Tea": "₹90"
                }
            },
            "restaurant_2": {
                "name": "Sukiyabashi Jiro",
                "menu": {
                    "Omakase Sushi": "₹18,000",
                    "Tuna Sushi": "₹3,000",
                    "Miso Soup": "₹480"
                }
            },
            "restaurant_3": {
                "name": "Gyukatsu Motomura",
                "menu": {
                    "Beef Cutlet Set": "₹1,800",
                    "Rice with Miso Soup": "₹900",
                    "Green Salad": "₹600"
                }
            },
            "restaurant_4": {
                "name": "Tsukiji Outer Market",
                "menu": {
                    "Grilled Eel": "₹1,200",
                    "Fresh Sushi Platter": "₹2,400",
                    "Matcha Ice Cream": "₹600"
                }
            }
        }
    },

    "sydney": {
        "tourism": ["Sydney Opera House", "Harbour Bridge", "Bondi Beach", "Blue Mountains"],
        "hotels": {
            "low_budget_hotels": [
                "Wake Up! Sydney",
                "Bounce Sydney",
                "Sydney Central Inn",
                "The Pod Sydney",
                "budget: ₹3,300 – ₹8,250 per day"
            ],
            "high_budget_hotels": [
                "Park Hyatt Sydney",
                "The Langham Sydney",
                "budget: ₹27,500 – ₹66,000 per day"
            ]
        },
        "restaurants": {
            "restaurant_1": {
                "name": "Quay Restaurant",
                "menu": {
                    "Seafood Tasting Menu": "₹13,750",
                    "Lamb with Native Spices": "₹9,900",
                    "Pavlova": "₹4,950"
                }
            },
            "restaurant_2": {
                "name": "Hurricane’s Grill",
                "menu": {
                    "BBQ Ribs": "₹2,475",
                    "Steak": "₹3,300",
                    "Garlic Bread": "₹660"
                }
            },
            "restaurant_3": {
                "name": "Bills Darlinghurst",
                "menu": {
                    "Ricotta Hotcakes": "₹1,650",
                    "Scrambled Eggs": "₹990",
                    "Flat White Coffee": "₹495"
                }
            },
            "restaurant_4": {
                "name": "The Grounds of Alexandria",
                "menu": {
                    "Avocado Toast": "₹1,100",
                    "Grilled Salmon Bowl": "₹2,200",
                    "Iced Coffee": "₹550"
                }
            }
        }
    }
}

#------------------------------------------------------------------------------------------------------------

@router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    query = request.query.lower()

    # 1. Check Indian Capitals
    for capital, data in INDIA_CAPITALS.items():
        if capital in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # 2. Check Indian States
    for state, data in INDIA_STATES.items():
        if state in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # 3. Check World Cities
    for city, data in WORLD_TOURISM.items():
        if city in query:
            return {"query": request.query, "tourism_places": data["tourism"], "hotels": data["hotels"], "restaurants":data["restaurants"]}

    # Default Response
    return {
        "query": request.query,
        "suggestions": [
            "Sorry, no direct match found.",
            "Try searching with a state, capital city, or world-famous destination."
        ]
    }

#------------------------------------------------------------------------------------------------------------

# --------------------
# Search Plans
# --------------------
@router.get("/search")
async def search(destination: str):
    cursor = plans_collection.find(
        {"destination": {"$regex": destination, "$options": "i"}}
    ).sort("created_at", -1).limit(20)

    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "destination": doc.get("destination", "Unknown"),
            "created_at": str(doc.get("created_at", "")),
            "snippet": (doc.get("plan_text", "")[:250] + "...") if len(doc.get("plan_text", "")) > 250 else doc.get("plan_text", "")
        })

    if results:
        return {"results": results, "source": "mongodb"}

    # fallback: search in static datasets
    dest = destination.lower()
    if dest in INDIA_STATES:
        return {"destination": destination, "tourism": INDIA_STATES[dest]["tourism"], "hotels": INDIA_STATES[dest]["hotels"], "source": "static:INDIA_STATES"}
    elif dest in WORLD_TOURISM:
        return {"destination": destination, "tourism": WORLD_TOURISM[dest]["tourism"], "hotels": WORLD_TOURISM[dest]["hotels"], "source": "static:WORLD_TOURISM"}

    raise HTTPException(status_code=404, detail="Destination not found")


#------------------------------------------------------------------------------------------------------------

# --------------------
# Feedback
# --------------------
@router.post("/feedback")
async def feedback(plan_id: str, rating: int = 5, comment: str = ""):
    doc = {
        "plan_id": plan_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    }
    await feedback_collection.insert_one(doc)
    return {"ok": True}

#------------------------------------------------------------------------------------------------------------

# --------------------
# Group Trip Planner
# --------------------

@router.post("/group_trip")
async def group_trip(req: GroupTripRequest):
    query = req.destination.lower()
    per_person_budget = req.total_budget // req.members

    # Search in Capitals
    for capital, data in INDIA_CAPITALS.items():
        if capital in query:
            return {
                "destination": capital.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"]
            }

    # Search in States
    for state, data in INDIA_STATES.items():
        if state in query:
            return {
                "destination": state.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"]
            }

    # Search in World Tourism
    for city, data in WORLD_TOURISM.items():
        if city in query:
            return {
                "destination": city.title(),
                "total_budget": req.total_budget,
                "members": req.members,
                "per_person_budget": per_person_budget,
                "tourism_places": data["tourism"],
                "recommended_hotel": data["hotels"]["low_budget_hotels"][0],
                "recommended_restaurant": data["restaurants"]["restaurant_1"]["name"]
            }

    return {"error": "Destination not found in our database."}

#------------------------------------------------------------------------------------------------------------

# --------------------
# Create Group Trip
# --------------------
@router.post("/group-trip")
async def create_group_trip(req: GroupTripRequest):
    try:
        # Check if trip already exists
        existing = await plans_collection.find_one({"trip_id": req.trip_id})
        if existing:
            raise HTTPException(status_code=400, detail="Trip ID already exists. Please choose another.")

        doc = {
            "trip_id": req.trip_id,
            "destination": req.destination,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "budget": req.budget,
            "transport_mode": req.transport_mode,
            "travelers": [traveler.dict() for traveler in req.travelers],
            "created_at": datetime.utcnow()
        }

        await plans_collection.insert_one(doc)
        return {"message": "Group trip created successfully ✅", "trip": doc}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#------------------------------------------------------------------------------------------------------------

# --------------------
# Booking Trip
# --------------------
@router.post("/book")
async def book_trip(req: BookingRequest):
    booking_summary = {
        "user_id": req.user_id,
        "destination": req.destination,
        "budget": req.budget,
        "transport_mode": req.transport_mode,
        "status": "Booking Confirmed ✅",
        "details": []
    }

    # --------------------------
    # Find hotels & restaurants for destination
    # --------------------------
    destination = req.destination.lower()
    hotels = {}
    restaurants = {}

    if destination in INDIA_CAPITALS:
        hotels = INDIA_CAPITALS[destination]["hotels"]
        restaurants = INDIA_CAPITALS[destination]["restaurants"]
    elif destination in INDIA_STATES:
        hotels = INDIA_STATES[destination]["hotels"]
        restaurants = INDIA_STATES[destination]["restaurants"]
    elif destination in WORLD_TOURISM:
        hotels = WORLD_TOURISM[destination]["hotels"]
        restaurants = WORLD_TOURISM[destination]["restaurants"]

    # --------------------------
    # Auto-select hotel & restaurant based on budget
    # --------------------------
    if req.budget <= 15000:  # low budget trip
        selected_hotel = hotels.get("low_budget_hotels", ["Default Budget Hotel"])[0]
        selected_restaurant = list(restaurants.values())[0]["name"] if restaurants else "Default Budget Restaurant"
    else:  # high budget trip
        selected_hotel = hotels.get("high_budget_hotels", ["Default Luxury Hotel"])[0]
        selected_restaurant = list(restaurants.values())[1]["name"] if restaurants else "Default Luxury Restaurant"

    booking_summary["hotel"] = selected_hotel
    booking_summary["restaurant"] = selected_restaurant

    # --------------------------
    # Transport booking with vehicle details
    # --------------------------
    if req.transport_mode == "train":
        booking_summary["details"].append("Train tickets booked: Rajdhani Express 🚆")
    elif req.transport_mode == "flight":
        booking_summary["details"].append("Flight booked: Air India AI-202 ✈️")
    elif req.transport_mode == "bus":
        booking_summary["details"].append("Bus booked: VRL Volvo AC Sleeper 🚌")
    else:
        booking_summary["details"].append("Invalid transport mode. Please choose train, flight, or bus.")

    # --------------------------
    # Add hotel & restaurant booking details
    # --------------------------
    booking_summary["details"].append(f"Hotel booked: {selected_hotel}")
    booking_summary["details"].append(f"Restaurant reserved: {selected_restaurant}")

    # --------------------------
    # Expense breakdown (50% transport, 30% hotel, 20% food)
    # --------------------------
    booking_summary["expense_breakdown"] = {
        "transport": f"₹{int(req.budget * 0.5)}",
        "hotel": f"₹{int(req.budget * 0.3)}",
        "food": f"₹{int(req.budget * 0.2)}"
    }

    return booking_summary
