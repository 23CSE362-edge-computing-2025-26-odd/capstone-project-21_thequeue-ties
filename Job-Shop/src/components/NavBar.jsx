// components/NavBar.jsx
import styled from "styled-components";

const Container = styled.div`
  width: 100%;
  height: 10vh;
`;

const HeaderContainer = styled.div`
  display: flex;
  border-bottom: 2px solid black;
`;

const Header = styled.h1`
  font-size: 24px;
  border: ${(props) => (props.active ? "1px solid black" : "none")};
  display: flex;
  height: 100%;
  margin: 0px;
  padding: 10px 5px;
  border-bottom: 0px;
  cursor: pointer;
`;

const NavBar = ({ activeTab, onChange }) => (
  <Container>
    <HeaderContainer>
      <Header active={activeTab === "Machine"} onClick={() => onChange("Machine")}>
        Machine
      </Header>
      <Header active={activeTab === "Jobs"} onClick={() => onChange("Jobs")}>
        Jobs
      </Header>
    </HeaderContainer>
  </Container>
);

export default NavBar;
