"""Chart calculation API endpoints."""

from datetime import datetime, timezone, date, time
from typing import Dict, Any
import logging
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import ValidationError

from app.models.chart import ChartRequest, ChartData, BirthDetails, ChartPreferences, PlanetPosition, HousePosition
from app.models.chart_models import BirthChart
from app.core.ephemeris import EphemerisCalculator, get_sign_name, get_nakshatra_name
from app.core.houses import HouseSystemCalculator
from app.core.dasha import VimshottariDasha
from app.core.divisional_charts import DivisionalChartCalculator
from app.core.yogas import YogaDetector
from app.core.aspects import VedicAspectCalculator
from app.core.transits import TransitCalculator
from app.core.shadbala import ShadbalaCalculator
from app.core.planetary_relationships import PlanetaryRelationshipAnalyzer
from app.core.ashtakavarga import AshtakavargaCalculator
from app.core.dasha_intensity import DashaIntensityCalculator
from app.services.pdf_generator import PDFReportGenerator
from app.services.image_generator import ImageGenerator
from app.core.database import get_db
from app.core.rbac import get_current_user_or_guest
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


def convert_datetime_objects(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetime_objects(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_datetime_objects(item) for item in obj]
    return obj


@router.get("/test")
async def test_chart_api():
    """Test endpoint to verify chart API is working."""
    return {
        "status": "healthy",
        "message": "Chart API is operational",
        "endpoints": [
            "POST /api/v1/chart/calculate - Calculate Vedic chart",
            "GET /api/v1/chart/test - This test endpoint"
        ]
    }


@router.post("/calculate", response_model=Dict[str, Any])
async def calculate_chart(
    request: ChartRequest,
    user = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate Vedic horoscope chart from birth details.

    Args:
        request: Chart calculation request with birth details and preferences
        user: Current user (authenticated or guest)
        db: Database session

    Returns:
        Complete chart data including planetary positions, houses, and metadata
    """
    try:
        logger.info(f"Calculating chart for birth date: {request.birth_details.date} (user: {user.email})")

        # Extract birth details
        birth_details = request.birth_details
        preferences = request.preferences or ChartPreferences()

        # Create datetime object from birth details
        if birth_details.time_unknown:
            # Default to 12:00 PM if time is unknown
            birth_datetime = datetime.combine(
                birth_details.date,
                datetime.min.time().replace(hour=12)
            )
        else:
            birth_datetime = datetime.combine(birth_details.date, birth_details.time)

        # Add timezone info (simplified - in production, use proper timezone handling)
        # For now, treat as naive datetime to avoid timezone comparison issues
        # birth_datetime = birth_datetime.replace(tzinfo=timezone.utc)

        # Initialize calculators
        ephemeris = EphemerisCalculator(ayanamsha=preferences.ayanamsha)
        house_calc = HouseSystemCalculator(house_system=preferences.house_system)
        dasha_calc = VimshottariDasha()
        divisional_calc = DivisionalChartCalculator()
        yoga_detector = YogaDetector()
        aspect_calc = VedicAspectCalculator()
        shadbala_calc = ShadbalaCalculator()
        relationship_analyzer = PlanetaryRelationshipAnalyzer()
        ashtakavarga_calc = AshtakavargaCalculator()

        # Calculate planetary positions
        planet_positions = ephemeris.calculate_all_planets(birth_datetime)

        # Calculate ascendant and houses using the selected house system
        ascendant_data = ephemeris.calculate_ascendant(
            birth_datetime,
            birth_details.latitude,
            birth_details.longitude,
            house_system=preferences.house_system
        )

        house_data = house_calc.calculate_houses(
            birth_datetime,
            birth_details.latitude,
            birth_details.longitude,
            ascendant_data.get('ayanamsha_value', 0.0)
        )

        # Calculate Dasha periods
        moon_position = planet_positions.get('Moon', {})
        moon_longitude = moon_position.get('sidereal_longitude', 0.0)

        current_dasha = dasha_calc.get_current_dasha(
            birth_datetime,
            moon_longitude
        )

        dasha_timeline = dasha_calc.get_dasha_timeline(
            birth_datetime,
            moon_longitude,
            years_ahead=12  # Calculate 12 years from birth date for performance
        )

        # Calculate comprehensive dasha navigator data
        dasha_navigator = dasha_calc.get_comprehensive_dasha_navigator(
            birth_datetime,
            moon_longitude,
            years_ahead=120  # Full 120-year cycle
        )

        # Calculate divisional charts including defaults and user selections
        all_divisional_charts = preferences.get_all_divisional_charts()
        divisional_charts = divisional_calc.calculate_all_divisional_charts(
            planet_positions,
            chart_types=all_divisional_charts
        )

        # Convert to response format
        planets = []
        for planet_name, pos_data in planet_positions.items():
            planet = PlanetPosition(
                name=planet_name,
                tropical_longitude=pos_data['tropical_longitude'],
                sidereal_longitude=pos_data['sidereal_longitude'],
                sign=get_sign_name(pos_data['sign_number']),
                degree_in_sign=pos_data['degree_in_sign'],
                nakshatra=get_nakshatra_name(pos_data['nakshatra_number']),
                pada=pos_data['pada'],
                house=((pos_data['sign_number'] - ascendant_data['sign_number']) % 12) + 1,
                retrograde=pos_data['retrograde'],
                speed=pos_data['speed']
            )
            planets.append(planet)

        # Convert house data
        houses = []
        if 'house_cusps_sidereal' in house_data:
            for i, house_cusp in enumerate(house_data['house_cusps_sidereal']):
                house = HousePosition(
                    number=i + 1,
                    cusp_longitude=house_cusp,
                    sign=get_sign_name(int(house_cusp / 30)),
                    degree_in_sign=house_cusp % 30
                )
                houses.append(house)

        # Create chart data
        chart_data = ChartData(
            birth_info=birth_details,
            preferences=preferences,
            ascendant=house_data.get('ascendant_sidereal', 0.0),
            ascendant_sign=get_sign_name(int(house_data.get('ascendant_sidereal', 0.0) / 30)),
            planets=planets,
            houses=houses,
            ayanamsha_value=ascendant_data.get('ayanamsha_value', 0.0)
        )

        # Detect yogas
        yogas = yoga_detector.detect_all_yogas(
            [planet.dict() for planet in planets],
            [house.dict() for house in houses],
            chart_data.ascendant_sign
        )

        # Convert yogas to dict format
        yogas_data = []
        for yoga in yogas:
            yogas_data.append({
                "name": yoga.name,
                "type": yoga.type,
                "strength": yoga.strength,
                "description": yoga.description,
                "planets_involved": yoga.planets_involved,
                "houses_involved": yoga.houses_involved,
                "conditions_met": yoga.conditions_met,
                "effects": yoga.effects
            })

        # Calculate aspects
        aspects = aspect_calc.calculate_all_aspects(
            [planet.dict() for planet in planets],
            [house.dict() for house in houses]
        )

        # Convert aspects to dict format
        aspects_data = []
        for aspect in aspects:
            aspects_data.append({
                "aspecting_planet": aspect.aspecting_planet,
                "aspected_planet": aspect.aspected_planet,
                "aspected_house": aspect.aspected_house,
                "aspect_type": aspect.aspect_type,
                "aspect_strength": aspect.aspect_strength,
                "orb": aspect.orb,
                "description": aspect.description,
                "benefic": aspect.benefic
            })

        # Get aspect summary
        aspect_summary = aspect_calc.get_aspect_summary(aspects)

        # Calculate Shadbala (planetary strengths)
        shadbala_results = shadbala_calc.calculate_shadbala(
            birth_datetime, birth_details.latitude, birth_details.longitude,
            [planet.dict() for planet in planets],
            [house.dict() for house in houses]
        )

        # Calculate planetary relationships
        relationship_results = relationship_analyzer.analyze_relationships(
            [planet.dict() for planet in planets]
        )

        # Calculate Ashtakavarga
        ashtakavarga_results = ashtakavarga_calc.calculate_ashtakavarga(
            [planet.dict() for planet in planets],
            [house.dict() for house in houses]
        )

        logger.info(f"Chart calculation completed successfully with {len(yogas)} yogas, {len(aspects)} aspects, and Shadbala analysis")

        # Prepare complete chart data - convert date/time objects to strings for JSON serialization
        chart_data_dict = chart_data.dict()

        complete_chart_data = {
            **chart_data_dict,
            "current_dasha": current_dasha,
            "dasha_timeline": dasha_timeline,
            "dasha_navigator": dasha_navigator,
            "divisional_charts": divisional_charts,
            "yogas": yogas_data,
            "aspects": aspects_data,
            "aspect_summary": aspect_summary,
            "shadbala": shadbala_results,
            "planetary_relationships": relationship_results,
            "ashtakavarga": ashtakavarga_results
        }

        # Recursively convert all datetime objects to ISO format strings
        complete_chart_data = convert_datetime_objects(complete_chart_data)

        # Save chart to database if user is authenticated (not guest)
        chart_id = None
        if user.id != "guest-demo-user":
            try:
                birth_chart = BirthChart(
                    user_id=user.id,
                    name=birth_details.name or f"Chart - {birth_details.date}",
                    birth_date=birth_details.date,
                    birth_time=birth_details.time,
                    birth_latitude=birth_details.latitude,
                    birth_longitude=birth_details.longitude,
                    birth_timezone=birth_details.timezone,
                    birth_location=birth_details.location_name,
                    ayanamsha=preferences.ayanamsha,
                    house_system=preferences.house_system,
                    chart_style=preferences.chart_style,
                    chart_data=complete_chart_data,
                    is_public="N",
                )
                db.add(birth_chart)
                await db.commit()
                await db.refresh(birth_chart)
                chart_id = birth_chart.id
                logger.info(f"Chart saved to database with ID: {chart_id}")
            except Exception as e:
                logger.error(f"Error saving chart to database: {e}")
                # Don't fail the request if database save fails
                pass

        response_data = {
            "success": True,
            "data": complete_chart_data,
            "message": "Chart calculated successfully"
        }

        # Include chart ID if saved
        if chart_id:
            response_data["chart_id"] = chart_id
            response_data["message"] = "Chart calculated and saved successfully"

        return response_data

    except ValidationError as e:
        logger.error(f"Validation error in chart calculation: {e}")
        # Extract detailed validation errors
        error_details = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            error_details.append(f"{field}: {message}")

        raise HTTPException(
            status_code=422,
            detail={
                "error": "Validation failed",
                "details": error_details,
                "message": "Please check your input data and try again"
            }
        )

    except ValueError as e:
        logger.error(f"Value error in chart calculation: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid input data",
                "message": str(e)
            }
        )

    except Exception as e:
        logger.error(f"Error calculating chart: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred during chart calculation"
            }
        )


@router.get("/sample")
async def get_sample_chart():
    """
    Get a sample chart for testing and demonstration purposes.

    Returns:
        Sample chart data with mock birth details
    """
    try:
        # Create sample birth details
        from datetime import time as time_type, date as date_type
        sample_birth = BirthDetails(
            name="Sample Person",
            date=date_type(1990, 6, 15),
            time=time_type(14, 30),
            time_unknown=False,
            latitude=28.6139,  # New Delhi
            longitude=77.2090,
            timezone="Asia/Kolkata",
            location_name="New Delhi, India"
        )

        sample_request = ChartRequest(
            birth_details=sample_birth,
            preferences=ChartPreferences()
        )

        # Calculate the sample chart
        return await calculate_chart(sample_request)

    except Exception as e:
        logger.error(f"Error generating sample chart: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating sample chart: {str(e)}"
        )


@router.post("/export/pdf")
async def export_chart_pdf(request: ChartRequest):
    """
    Export Vedic horoscope chart as PDF report.

    Args:
        request: Chart calculation request with birth details and preferences

    Returns:
        PDF file as binary response
    """
    try:
        logger.info("Generating PDF export for chart")

        # First calculate the chart (reuse the calculation logic)
        chart_response = await calculate_chart(request)

        if not chart_response.get("success"):
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate chart for PDF export"
            )

        chart_data = chart_response["data"]

        # Generate PDF
        pdf_generator = PDFReportGenerator()
        pdf_bytes = pdf_generator.generate_chart_report(chart_data)

        if pdf_bytes is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate PDF report"
            )

        # Create filename
        birth_info = chart_data.get('birth_info', {})
        name = birth_info.get('name', 'chart')
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_name:
            safe_name = "vedic_chart"

        filename = f"{safe_name}_vedic_chart.pdf"

        # Return PDF response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting chart as PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export chart as PDF"
        )


@router.post("/export/svg")
async def export_chart_svg(request: ChartRequest):
    """
    Export chart as SVG image.

    Args:
        request: Chart calculation request

    Returns:
        SVG image response
    """
    try:
        logger.info("Generating SVG export")

        # Calculate chart data (reuse existing logic)
        chart_response = await calculate_chart(request)
        chart_data = chart_response["data"]

        # Initialize image generator
        image_gen = ImageGenerator()

        # Generate SVG
        svg_content = image_gen.generate_chart_svg(chart_data, chart_style="north")

        logger.info("SVG export completed successfully")

        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Content-Disposition": "attachment; filename=vedic_chart.svg"
            }
        )

    except Exception as e:
        logger.error(f"Error generating SVG: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating SVG: {str(e)}")


@router.post("/export/png")
async def export_chart_png(request: ChartRequest):
    """
    Export chart as PNG image.

    Args:
        request: Chart calculation request

    Returns:
        PNG image response
    """
    try:
        logger.info("Generating PNG export")

        # Calculate chart data (reuse existing logic)
        chart_response = await calculate_chart(request)
        chart_data = chart_response["data"]

        # Initialize image generator
        image_gen = ImageGenerator()

        # Generate PNG
        png_bytes = image_gen.generate_chart_png(chart_data, chart_style="north", size=800)

        logger.info("PNG export completed successfully")

        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=vedic_chart.png"
            }
        )

    except Exception as e:
        logger.error(f"Error generating PNG: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PNG: {str(e)}")


@router.post("/export/json")
async def export_chart_json(request: ChartRequest):
    """
    Export complete chart data as JSON.

    Args:
        request: Chart calculation request

    Returns:
        JSON response with complete chart data
    """
    try:
        logger.info("Generating JSON export")

        # Calculate chart data (reuse existing logic)
        chart_response = await calculate_chart(request)

        if not chart_response.get("success"):
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate chart for JSON export"
            )

        chart_data = chart_response["data"]

        # Create comprehensive JSON export
        json_export = {
            "export_info": {
                "format": "json",
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "software": "Vedic Horoscope Chart Pack"
            },
            "birth_details": {
                "name": request.birth_details.name,
                "date": request.birth_details.date.isoformat(),
                "time": request.birth_details.time.isoformat() if request.birth_details.time else None,
                "time_unknown": request.birth_details.time_unknown,
                "location": {
                    "name": request.birth_details.location_name,
                    "latitude": request.birth_details.latitude,
                    "longitude": request.birth_details.longitude,
                    "timezone": request.birth_details.timezone
                }
            },
            "chart_preferences": {
                "ayanamsha": request.preferences.ayanamsha if request.preferences else "LAHIRI",
                "house_system": request.preferences.house_system if request.preferences else "WHOLE_SIGN"
            },
            "chart_data": chart_data
        }

        logger.info("JSON export completed successfully")

        return Response(
            content=json.dumps(json_export, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=vedic_chart.json"
            }
        )

    except Exception as e:
        logger.error(f"Error generating JSON export: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating JSON export: {str(e)}")


@router.post("/intensity-analysis")
async def calculate_intensity_analysis(
    request: ChartRequest,
    user_or_guest = Depends(get_current_user_or_guest),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate Dasha-Bhukti intensity analysis for life areas.

    Args:
        request: Chart calculation request
        user_or_guest: Current user or guest
        db: Database session

    Returns:
        Intensity analysis with scores and reasoning for 6 life areas
    """
    try:
        logger.info("Starting Dasha-Bhukti intensity analysis")

        # First calculate the chart (reuse the calculation logic)
        chart_response = await calculate_chart(request, user_or_guest, db)

        if not chart_response.get("success"):
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate chart for intensity analysis"
            )

        chart_data = chart_response["data"]

        # Calculate intensity analysis
        intensity_calc = DashaIntensityCalculator()
        intensity_results = intensity_calc.calculate_all_intensities(chart_data)

        if not intensity_results.get('success', False):
            error_msg = intensity_results.get('error', 'Unknown error in intensity calculation')
            logger.error(f"Intensity calculation failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Intensity calculation failed: {error_msg}"
            )

        logger.info(f"Intensity analysis completed successfully with {intensity_results.get('total_periods', 0)} periods")

        return {
            "success": True,
            "data": intensity_results,
            "message": "Dasha-Bhukti intensity analysis calculated successfully"
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error calculating intensity analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating intensity analysis: {str(e)}"
        )