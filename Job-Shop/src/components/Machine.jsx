import React, { useState, useCallback } from "react";
import styled, { css } from "styled-components";

const DURATION = 300;

const Container = styled.div`
  width: 100%;
  position: relative;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-family: Arial, sans-serif;
`;

const Th = styled.th`
  border: 1px solid #ccc;
  padding: 10px;
  background-color: #f2f2f2;
  text-align: left;
`;

const Td = styled.td`
  border: 1px solid #ccc;
  padding: 10px;
`;

const Tr = styled.tr`
  &:nth-child(even) {
    background-color: #fafafa;
  }
  &:hover {
    background-color: #f0f8ff;
    cursor: pointer;
  }
`;

const BlurLayer = styled.div`
  position: absolute;
  inset: 0;
  z-index: 5;
  opacity: 0;
  pointer-events: none;
  transition: opacity ${DURATION}ms ease-in-out;

  @supports ((backdrop-filter: blur(2px)) or (-webkit-backdrop-filter: blur(2px))) {
    -webkit-backdrop-filter: blur(2px);
    backdrop-filter: blur(2px);
  }

  ${props => props.$visible && css`
    opacity: 1;
    pointer-events: auto;
  `}
`;

const Details = styled.div`
  background-color: #111;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  height: 70vh;
  width: 55vw;
  position: absolute;
  top: 7%;
  left: 20%;
  z-index: 10;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);

  opacity: 0;
  transform: translateY(8px) scale(0.98);
  pointer-events: none; 
  transition:
    opacity ${DURATION}ms ease-in-out,
    transform ${DURATION}ms ease-in-out;

  ${props => props.$visible && css`
    opacity: 1;
    transform: translateY(0) scale(1);
    pointer-events: auto; 
  `}
`;

const CloseBtn = styled.button`
  align-self: flex-end;
  background: #333;
  color: #fff;
  border: none;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
`;

const data = [
  { machineId: "A_01", machineName: "CNC Mill A", description: "3-axis milling, drilling, slotting; aluminum/steel parts up to 400x300 mm", temperatureC: 46.2, status: "Operational" },
  { machineId: "A_02", machineName: "Lathe A", description: "Turning, facing, threading; bar feed up to 40 mm; rough and finish passes", temperatureC: 51.8, status: "Operational" },
  { machineId: "B_07", machineName: "Injection Molder", description: "ABS/PP molding, cycle optimization, in-mold labeling; 120-ton clamp", temperatureC: 62.5, status: "Idle" },
  { machineId: "C_03", machineName: "Pick-and-Place SMD", description: "0402–SOIC placement, feeder changeover, paste inspection assist", temperatureC: 38.4, status: "Operational" },
  { machineId: "Q_12", machineName: "CMM Quality Station", description: "Coordinate measurement, GD&T checks, SPC sampling for shafts and housings", temperatureC: 25.6, status: "Operational" },
  { machineId: "P_05", machineName: "Press Brake", description: "Sheet metal bending 1–3 mm, 1000 mm width, multi-bend sequences", temperatureC: 44.1, status: "Down" },
  { machineId: "M_09", machineName: "Surface Grinder", description: "Surface grinding to Ra 0.4 µm, parallelism < 10 µm; tool reconditioning", temperatureC: 55.0, status: "Operational" },
  { machineId: "W_02", machineName: "Welding Cell", description: "MIG/TIG welds, fixture-based assemblies; post-weld visual inspection", temperatureC: 47.3, status: "Operational" },
  { machineId: "P_21", machineName: "Paint Booth", description: "Primer and top-coat spray, curing schedule control, quick color changeover", temperatureC: 29.8, status: "Idle" },
  { machineId: "A_15", machineName: "CNC Mill B", description: "High-speed finishing, indexed 5-axis operations, small cavity machining", temperatureC: 58.6, status: "Faulty" }
];

const Machine = () => {
  const [selectedMachine, setSelectedMachine] = useState(null);
  const [isOpen, setIsOpen] = useState(false); 

  const openDetails = useCallback((row) => {
    setSelectedMachine(row);  
    setIsOpen(true);          
  }, []);

  const closeDetails = useCallback(() => {
    setIsOpen(false);       
    
  }, []);

  return (
    <Container>
      <Table>
        <thead>
          <Tr>
            <Th>Machine No:</Th>
            <Th>Machine Name</Th>
            <Th>Description</Th>
            <Th>Temperature</Th>
            <Th>Status</Th>
          </Tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <Tr key={row.machineId} onClick={() => openDetails(row)}>
              <Td>{row.machineId}</Td>
              <Td>{row.machineName}</Td>
              <Td>{row.description}</Td>
              <Td>{row.temperatureC} °C</Td>
              <Td>{row.status}</Td>
            </Tr>
          ))}
        </tbody>
      </Table>


      <BlurLayer $visible={isOpen} onClick={closeDetails} />
      <Details
        $visible={isOpen}
        role="dialog"
        aria-modal="true"
        aria-hidden={!isOpen}
      >
        <CloseBtn onClick={closeDetails}>Close</CloseBtn>
        {selectedMachine && (
          <>
            <h2 style={{ margin: 0 }}>{selectedMachine.machineName}</h2>
            <div><strong>ID:</strong> {selectedMachine.machineId}</div>
            <div><strong>Status:</strong> {selectedMachine.status}</div>
            <div><strong>Temperature:</strong> {selectedMachine.temperatureC} °C</div>
            <div><strong>Description:</strong> {selectedMachine.description}</div>
          </>
        )}
      </Details>
    </Container>
  );
};

export default Machine;
