import React from "react";
import color from "../config/colors";
import styled from "styled-components";
import { Container as BootstrapContainer } from "react-bootstrap";

const Background = styled.div`
  background-color: ${color.BLUE};
`;

const Container = styled(BootstrapContainer)`
  padding: 1.5em 0.8em;
`;
const MainBar = props => (
  <Background>
    <Container>
      <div className="pt-4 pb-4">
        <h1 className="text-white">{props.MainBarHeader}</h1>
        <p className="text-white" style={{ fontSize: "18px" }}>
          {props.MainBarText}
        </p>
      </div>
    </Container>
  </Background>
);

export default MainBar;
