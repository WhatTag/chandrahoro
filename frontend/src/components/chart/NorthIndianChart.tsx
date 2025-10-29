import React from 'react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { PlanetTooltip, HouseTooltip } from '@/components/chart/ChartTooltip';
import type { ChartData } from '@/lib/api';

interface NorthIndianChartProps {
  chartData: ChartData;
  size?: number;
}

interface HouseData {
  number: number;
  planets: string[];
  sign: string;
}

export default function NorthIndianChart({ chartData, size = 400 }: NorthIndianChartProps) {
  // Create house data with planets
  const houses: HouseData[] = Array.from({ length: 12 }, (_, i) => ({
    number: i + 1,
    planets: [],
    sign: chartData.houses[i]?.sign || ''
  }));

  // Place planets in houses
  chartData.planets.forEach(planet => {
    if (planet.house >= 1 && planet.house <= 12) {
      houses[planet.house - 1].planets.push(planet.name);
    }
  });

  // North Indian chart house positions (diamond layout)
  const housePositions = [
    { x: 50, y: 0, width: 50, height: 25 },   // House 1 (top right)
    { x: 75, y: 25, width: 25, height: 25 },  // House 2 (right top)
    { x: 75, y: 50, width: 25, height: 25 },  // House 3 (right bottom)
    { x: 50, y: 75, width: 50, height: 25 },  // House 4 (bottom right)
    { x: 25, y: 75, width: 25, height: 25 },  // House 5 (bottom left)
    { x: 0, y: 50, width: 25, height: 25 },   // House 6 (left bottom)
    { x: 0, y: 25, width: 25, height: 25 },   // House 7 (left top)
    { x: 0, y: 0, width: 25, height: 25 },    // House 8 (top left)
    { x: 25, y: 0, width: 25, height: 25 },   // House 9 (top center left)
    { x: 25, y: 25, width: 25, height: 25 },  // House 10 (center left)
    { x: 25, y: 50, width: 25, height: 25 },  // House 11 (center bottom)
    { x: 50, y: 25, width: 25, height: 25 },  // House 12 (center right)
  ];

  // Get planet symbol
  const getPlanetSymbol = (planetName: string): string => {
    const symbols: { [key: string]: string } = {
      'Sun': '☉',
      'Moon': '☽',
      'Mercury': '☿',
      'Venus': '♀',
      'Mars': '♂',
      'Jupiter': '♃',
      'Saturn': '♄',
      'Rahu': '☊',
      'Ketu': '☋'
    };
    return symbols[planetName] || planetName.charAt(0);
  };

  // Get planet abbreviation
  const getPlanetAbbr = (planetName: string): string => {
    const abbr: { [key: string]: string } = {
      'Sun': 'Su',
      'Moon': 'Mo',
      'Mercury': 'Me',
      'Venus': 'Ve',
      'Mars': 'Ma',
      'Jupiter': 'Ju',
      'Saturn': 'Sa',
      'Rahu': 'Ra',
      'Ketu': 'Ke'
    };
    return abbr[planetName] || planetName.substring(0, 2);
  };

  // Get planet color based on benefic/malefic nature
  const getPlanetColor = (planetName: string): string => {
    const colors: { [key: string]: string } = {
      'Sun': '#f59e0b',      // Amber - neutral
      'Moon': '#3b82f6',     // Blue - benefic
      'Mercury': '#10b981',  // Green - neutral (depends on association)
      'Venus': '#3b82f6',    // Blue - benefic
      'Mars': '#ef4444',     // Red - malefic
      'Jupiter': '#3b82f6',  // Blue - benefic
      'Saturn': '#ef4444',   // Red - malefic
      'Rahu': '#8b5cf6',     // Purple - malefic
      'Ketu': '#8b5cf6'      // Purple - malefic
    };
    return colors[planetName] || '#6b7280';
  };

  // Check if planet is retrograde
  const isPlanetRetrograde = (planetName: string): boolean => {
    const planet = chartData.planets.find(p => p.name === planetName);
    return planet?.retrograde || false;
  };

  return (
    <TooltipProvider>
      <div className="flex flex-col items-center">
        <svg
          width={size}
          height={size}
          viewBox="0 0 100 100"
          className="border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
        >
        {/* Chart outline - diamond shape */}
        <path
          d="M 50 0 L 100 25 L 100 75 L 50 100 L 0 75 L 0 25 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.5"
          className="text-gray-700 dark:text-gray-300"
        />

        {/* Inner lines to create houses */}
        {/* Vertical center line */}
        <line x1="50" y1="0" x2="50" y2="100" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />

        {/* Horizontal lines */}
        <line x1="0" y1="25" x2="100" y2="25" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="0" y1="50" x2="100" y2="50" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="0" y1="75" x2="100" y2="75" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />

        {/* Vertical lines */}
        <line x1="25" y1="0" x2="25" y2="100" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="75" y1="25" x2="75" y2="75" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />

        {/* Diagonal lines for diamond shape */}
        <line x1="25" y1="0" x2="0" y2="25" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="75" y1="0" x2="100" y2="25" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="100" y1="75" x2="75" y2="100" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />
        <line x1="25" y1="100" x2="0" y2="75" stroke="currentColor" strokeWidth="0.3" className="text-gray-700 dark:text-gray-300" />

        {/* House numbers and planets */}
        {houses.map((house, index) => {
          const pos = housePositions[index];
          const centerX = pos.x + pos.width / 2;
          const centerY = pos.y + pos.height / 2;
          
          return (
            <g key={house.number}>
              {/* House number */}
              <text
                x={pos.x + 2}
                y={pos.y + 4}
                fontSize="3"
                fill="currentColor"
                fontWeight="bold"
                className="text-gray-600 dark:text-gray-400"
              >
                {house.number}
              </text>

              {/* Sign abbreviation */}
              <text
                x={centerX}
                y={pos.y + 8}
                fontSize="2.5"
                fill="currentColor"
                textAnchor="middle"
                fontStyle="italic"
                className="text-gray-500 dark:text-gray-500"
              >
                {house.sign.substring(0, 3)}
              </text>
              
              {/* Planets in this house */}
              {house.planets.map((planet, planetIndex) => {
                const planetColor = getPlanetColor(planet);
                const isRetrograde = isPlanetRetrograde(planet);
                const planetX = centerX - 6 + (planetIndex % 2) * 12;
                const planetY = centerY + 2 + Math.floor(planetIndex / 2) * 6;

                return (
                  <g key={planet}>
                    {/* Planet symbol */}
                    <text
                      x={planetX}
                      y={planetY}
                      fontSize="4"
                      fill={planetColor}
                      textAnchor="middle"
                      fontWeight="bold"
                      className="cursor-pointer hover:opacity-80"
                    >
                      {getPlanetSymbol(planet)}
                    </text>

                    {/* Planet abbreviation */}
                    <text
                      x={planetX}
                      y={planetY + 4}
                      fontSize="2"
                      fill={planetColor}
                      textAnchor="middle"
                      className="cursor-pointer hover:opacity-80"
                    >
                      {getPlanetAbbr(planet)}{isRetrograde ? 'R' : ''}
                    </text>

                    {/* Retrograde indicator circle */}
                    {isRetrograde && (
                      <circle
                        cx={planetX + 4}
                        cy={planetY - 2}
                        r="1"
                        fill={planetColor}
                        opacity="0.7"
                      />
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}
        
        {/* Ascendant marker */}
        <circle
          cx={housePositions[0].x + housePositions[0].width / 2}
          cy={housePositions[0].y + housePositions[0].height / 2}
          r="1"
          fill="#ef4444"
          stroke="#dc2626"
          strokeWidth="0.5"
        />
        
        {/* Ascendant label */}
        <text
          x={housePositions[0].x + housePositions[0].width / 2}
          y={housePositions[0].y + housePositions[0].height + 4}
          fontSize="2"
          fill="#ef4444"
          textAnchor="middle"
          fontWeight="bold"
        >
          ASC
        </text>
      </svg>
      
      {/* Legend */}
      <div className="mt-4 text-sm text-gray-600">
        <div className="grid grid-cols-3 gap-4 max-w-md">
          {chartData.planets.map(planet => (
            <div key={planet.name} className="flex items-center gap-2">
              <span
                className="text-lg font-bold"
                style={{ color: getPlanetColor(planet.name) }}
              >
                {getPlanetSymbol(planet.name)}
              </span>
              <span className="flex items-center gap-1">
                {planet.name}
                {planet.retrograde && (
                  <span className="text-xs bg-red-100 text-red-800 px-1 rounded">R</span>
                )}
              </span>
            </div>
          ))}
        </div>

        {/* Color coding explanation */}
        <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h4 className="font-medium mb-2 text-gray-900 dark:text-white">Color Coding:</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded"></div>
              <span>Benefic planets</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Malefic planets</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-amber-500 rounded"></div>
              <span>Neutral planets</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-purple-500 rounded"></div>
              <span>Shadow planets</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    </TooltipProvider>
  );
}
