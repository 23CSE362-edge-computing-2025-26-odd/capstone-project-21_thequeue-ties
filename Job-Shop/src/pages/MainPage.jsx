
import styled from "styled-components"
import NavBar from "../components/NavBar"
import Machine from "../components/Machine"
import Jobs from "../components/Jobs"
import { useState } from "react"



const Container = styled.div`
    height: 100vh;
`

const MainPage = () => {
  const [activeTab, setActiveTab] = useState("Machine");

  return (
    <Container>
      <NavBar activeTab={activeTab} onChange={setActiveTab} />
      {activeTab === "Machine" ? <Machine /> : <Jobs />}
    </Container>
  );
};

export default MainPage;