from scanner import Scanner
from tokens import Kind as K
from abstract_tree import *
from exceptions import (UnexpectedTokenException,
                        UnsupportedExpressionTokenException,
                        UnsupportedCommandTokenException,
                        UnsupportedDeclarationTokenException,
                        UnexpectedEndOfProgramException)


class Parser():
    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.current_terminal = scanner.scan()

    def parse_program(self) -> Program:
        command = self.parse_command()

        if self.current_terminal.kind is not K.EOT:
            raise UnexpectedEndOfProgramException(self.current_terminal)
        print(f"Successfully parsed the program.")
        return Program(command=command)

    def parse_command(self) -> Command:
        command = Command()
        while self.current_terminal.kind in [K.IDENTIFIER, K.FUNC,
                                             K.IF, K.WHILE, K.RETURN]:
            command.commands.append(self.parse_single_command())
        return command

    def parse_single_command(self) -> SingleCommand:
        if self.current_terminal.kind is K.FUNC:
            declaration = self.parse_declaration()
            return DeclarationCommand(declaration=declaration)
        elif self.current_terminal.kind in [K.RETURN, K.IF, K.WHILE]:
            statement = self.parse_single_statement()
            return StatementCommand(statement=statement)
        elif self.current_terminal.kind is K.IDENTIFIER:
            if self.current_terminal.spelling in ['int', 'str', 'bool']:
                declaration = self.parse_declaration()
                self.accept(K.SEMICOLON)
                return DeclarationCommand(declaration=declaration)
            else:
                statement = self.parse_single_statement()
                self.accept(K.SEMICOLON)
                return StatementCommand(statement=statement)
        else:
            raise UnsupportedCommandTokenException(
                current_token=self.current_terminal,
                current_line=self.scanner.current_line,
                current_column=self.scanner.current_column
            )

    def parse_single_statement(self):
        if self.current_terminal.kind is K.IF:
            self.accept(K.IF)
            self.accept(K.LEFT_PAR)
            expression = self.parse_expression()
            self.accept(K.RIGHT_PAR)
            self.accept(K.COLON)
            ifBlock = self.parse_command()
            if self.current_terminal.kind is K.ELSE:
                self.accept(K.ELSE)
                self.accept(K.COLON)
                elseBlock = self.parse_command()
            self.accept(K.END)
            return IfStatement(
                expr=expression,
                ifCom=ifBlock,
                elseCom=elseBlock
            )
        elif self.current_terminal.kind is K.WHILE:
            self.accept(K.WHILE)
            self.accept(K.LEFT_PAR)
            expression = self.parse_expression()
            self.accept(K.RIGHT_PAR)
            self.accept(K.COLON)
            command = self.parse_command()
            self.accept(K.END)
            return WhileStatement(
                expr=expression,
                command=command
            )
        elif self.current_terminal.kind is K.RETURN:
            self.accept(K.RETURN)
            expression = self.parse_single_expression()
            return ReturnStatement(expression)
        elif self.current_terminal.kind is K.IDENTIFIER:
            expressions = self.parse_expression()
            return ExpressionStatement(expressions=expressions)

    def parse_declaration(self):
        res = Declaration()
        while (self.current_terminal.kind is K.FUNC
                or self.current_terminal.spelling in ['int', 'str', 'bool']):
            res.declarations.append(self.parse_single_declaration())
        return res

    def parse_single_declaration(self):
        if self.current_terminal.kind is K.FUNC:
            self.accept(K.FUNC)
            identifier = self.accept(K.IDENTIFIER)
            self.accept(K.LEFT_PAR)
            args = self.parse_expressions_list()
            self.accept(K.RIGHT_PAR)
            self.accept(K.COLON)
            commands = self.parse_command()
            self.parse_command()
            self.accept(K.END)
            return FuncDeclaration(
                identifier=identifier,
                args=args,
                commands=commands
            )

        elif self.current_terminal.kind is K.IDENTIFIER:
            type_denoter = self.parse_type_denoter()
            identifier = self.parse_identifier()
            if self.current_terminal.kind is K.OPERATOR:
                operator = self.parse_operator()
                expression = self.parse_expression()
                return VarDeclarationWithAssignment(
                    type_denoter=type_denoter,
                    identifier=identifier,
                    operator=operator,
                    expression=expression)
            else:
                return VarDeclaration(
                    type_denoter=type_denoter,
                    identifier=identifier)

        else:
            raise UnsupportedDeclarationTokenException(
                current_token=self.current_terminal,
                current_line=self.scanner.current_line,
                current_column=self.scanner.current_column
            )

    def parse_expression(self):
        res = self.parse_single_expression()
        while self.current_terminal.kind is K.OPERATOR:
            operator = self.parse_operator()
            tmp = self.parse_single_expression()
            res = BinaryExpression(
                operator=operator,
                expression1=res,
                expression2=tmp)
        return res

    def parse_single_expression(self):
        if self.current_terminal.kind is K.INTEGER_LITERAL:
            literal = self.parse_integer_literal()
            return IntLiteralExpression(literal=literal)

        elif self.current_terminal.kind is K.BOOLEAN_LITERAL:
            boolean = self.parse_identifier()  # TODO: parse_boolean?
            return BooleanLiteralExpression(literal=boolean)

        elif self.current_terminal.kind is K.OPERATOR:
            operator = self.parse_operator()
            expression = self.parse_single_expression()
            return UnaryExpression(operator=operator, expression=expression)

        elif self.current_terminal.kind is K.IDENTIFIER:
            identifier = self.parse_identifier()
            # identifier()
            if self.current_terminal.kind is K.LEFT_PAR:
                self.accept(K.LEFT_PAR)
                expressions_list = self.parse_expressions_list()
                self.accept(K.RIGHT_PAR)
                return CallExpression(name=identifier, args=expressions_list)
            # identifier ~ expression
            elif self.current_terminal.kind is K.OPERATOR:
                variable = VarExpression(identifier)
                operator = self.parse_operator()
                expression = self.parse_expression()
                return BinaryExpression(
                    operator=operator,
                    expression1=variable,
                    expression2=expression
                )
            else:
                return VarExpression(identifier)

        else:
            raise UnsupportedExpressionTokenException(
                current_token=self.current_terminal,
                current_line=self.scanner.current_line,
                current_column=self.scanner.current_column
            )

    def parse_expressions_list(self):
        if self.current_terminal.kind in [K.IDENTIFIER, K.INTEGER_LITERAL, K.OPERATOR, K.BOOLEAN_LITERAL]:
            exp_list = ExpressionsList()
            expression = self.parse_expression()
            exp_list.expressions.append(expression)
            while self.current_terminal.kind is K.COMMA:
                self.accept(K.COMMA)
                exp_list.expressions.append(self.parse_expression())
            return exp_list

    def parse_type_denoter(self):
        spelling = self.parse_identifier()
        return TypeDenoter(spelling=spelling)

    def parse_integer_literal(self) -> IntegerLiteral:
        if self.current_terminal.kind is K.INTEGER_LITERAL:
            literal = IntegerLiteral(self.current_terminal.spelling)
            self.current_terminal = self.scanner.scan()
            return literal

    def parse_identifier(self) -> Identifier:
        if self.current_terminal.kind is K.IDENTIFIER:
            identifier = Identifier(self.current_terminal.spelling)
            self.current_terminal = self.scanner.scan()
            return identifier

    def parse_operator(self) -> Operator:
        if self.current_terminal.kind is K.OPERATOR:
            operator = Operator(self.current_terminal.spelling)
            self.current_terminal = self.scanner.scan()
            return operator
        else:
            raise UnexpectedTokenException(
                expected_kind=K.OPERATOR,
                current_token=self.current_terminal,
                current_line=self.scanner.current_line,
                current_column=self.scanner.current_column
            )

    def accept(self, token: K):
        if self.current_terminal.kind is token:
            self.current_terminal = self.scanner.scan()
            return True
        else:
            # return False
            raise UnexpectedTokenException(
                expected_kind=token,
                current_token=self.current_terminal,
                current_line=self.scanner.current_line,
                current_column=self.scanner.current_column
            )
