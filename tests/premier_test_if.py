from lark import Lark, Transformer

class Variable:
    """
    Structure de donnée permettant de représenter les objets variable dans un code Dumbo
    """
    INT = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    STRING_CONCAT = "STRING_CONCAT"
    LIST = "LIST"
    FOR_LIST = "FOR_LIST"
    REF = "REFERENCE"
    BOOL = "BOOLEAN"

    def __init__(self, name, type, value):
        self._name = name
        self._type = type
        self._value = value

    def get_name(self):
        """
        Retrourne le nom de la variable.
        """
        return self._name

    def get_type(self):
        """
        Retourne le type de la variable
        """
        return self._type

    def get(self):
        """
        Retourne la valeur de la variable
        """
        return self._value

    def __eq__(self, o):
        if isinstance(o, Variable):
            return (self._value == o.get() and self._type == o.get_type())

        return self._value == o

    def __str__(self):
        if self._type == Variable.LIST:
            return "(" + ",".join(self._value) + ")"
        return f"{self._value}"

    def __repr__(self):
        return f"{{{self._name} := {self._value} ({self._type})}}"

class Iterable(Variable):
    EOL = "EOL" #End Of List
    def __init__(self, *args):
        super(Iterable, self).__init__(*args)
        self.index = 0

    def get(self, index = None):
        if index:
            if (index < len(self._value)):
                return self._value[index]
            else:
                raise IndexError("list index out of range")
        
        if (self.index < len(self._value)):
            return self._value[self.index]
        else:
            raise IndexError("list index out of range")

    def next(self):
        try:
            result = self.get(index = self.index+1)
        except IndexError:
            result = Iterable.EOL
        return result

    def increment(self):
        self.index+=1

    def __str__(self):
        return "(" + ",".join(self._value) + ")"

    def __repr__(self):
        return f"{{{self._name} := {self._value[self.index]}, list size = {len(self._value)}, list content = {self._value}, current index = {self.index}}}"


class SymbolTable:
    """
    Structure de données représentant une table de symbole
    """
    def __init__(self, parent=None):
        self.parent = parent
        self._table = {}
        self._next = []

    def add_content(self, newc):
        """
        Ajout de l'élément newc dans la table de symboles
        """
        self._table.update({newc.get_name():newc})

    def add_depth(self, newd):
        """
        Ajout d'une nouvelle profondeur ou scope dans la table
        """
        self._next.append(newd)

    def get(self, k):
        """
        Récupération d'un élément dans la table
        """
        if k in self._table.keys():
            return self._table[k]
        elif self.parent:
            return self.parent.get(k)
        else:
            raise NameError(f"'{k}' not in symbol table")

    def change_value(self, k, newc):
        if k in self._table.keys():
            self._table[k] = newc
        elif self.parent:
            self.parent.change_value(k, newc)
        else:
            return NameError(f"'{k}' not in symbol table")

    def get_subscope(self):
        #return first subscope
        return self._next[0]

    def remove_scope(self, scope):
        self._next.remove(scope)

    def __contains__(self, o):
        if o in self._table.keys():
            return True
        elif self.parent:
            return o in self.parent
        else:
            return False

    def __str__(self):
        _ = "[\n"

        for key, value in self._table.items():
            _ += f"{key} := {value.get()} ({value.get_type()})\n"

        for elmnt in self._next:
            _ += f"{elmnt}\n"

        _ += "]"

        return _

    def __repr__(self):
        return str(self)


class IntermediateCodeHandler:
    def __init__(self):
        self.index = 0
        self.symbolTable = None
        self.stack = []
        self._output_buffer = ""

    def add_instr(self, instr):
        self.stack.append(instr)
        self.index +=1
        return self.index

    def execute(self, globalSymbolTable, DEBUG=False):
        self.symbolTable = globalSymbolTable

        if DEBUG:
            print("DEBUG MODE IS ON\n")
            print("STACK CONTENT:")
            for task in self.stack:
                print("\t"+ str(task))

        self.index = 0

        while self.index < len(self.stack):
            task = self.stack[self.index]

            if DEBUG:
                print("\nDEBUG:", task)

            if task.get_type() == AExpression.PRINT:
                if DEBUG:
                    print("DEBUG: PRINT STATEMENT")
                #afficher du contenu
                to_print = task.get_content()
                # si la variable à afficher n'est pas anonyme, elle est dans la table des symboles
                # donc il est possible que sa valeur ait été modifiée entre temps => on récupère la bonne valeur
                if to_print.get_name() != "__ANON__":
                    to_print = self.symbolTable.get(to_print.get_name())

                if to_print.get_type() == Variable.STRING_CONCAT:
                    to_add = ""
                    for item in to_print.get():
                        while item.get_type() == Variable.REF:
                            item = self.symbolTable.get(item.get())

                        to_add += str(item.get()) + " "
                    self._output_buffer += to_add + "\n"
                else:
                    while to_print.get_type() == Variable.REF:
                        to_print = self.symbolTable.get(to_print.get())

                    self._output_buffer += str(to_print.get()) + "\n"

                self.index += 1

            elif task.get_type() == AExpression.VAR:
                if DEBUG:
                    print("DEBUG: VARIABLE ASSIGNMENT")
                variable = task.get_content()
                #ajout d'une variable dans la mémoire si elle n'y est pas encore
                self.symbolTable.change_value(variable.get_name(), variable)

                self.index += 1

            elif task.get_type() == AExpression.FOR:
                if DEBUG:
                    print("DEBUG: BEGINNING FOR LOOP")

                #ajouter la loop variable dans ce scope ou check s'il n'existe pas déjà une variable de ce nom
                loop_var, iterable_var = task.get_content()
                #check si l'itérable est bien itérable
                while iterable_var.get_type() == Variable.REF:
                    iterable_var = self.symbolTable.get(iterable_var.get())
                if iterable_var.get_type() != Variable.LIST:
                    raise NameError(f"{iterable_var.get_name()} ({iterable_var.get_type()}) not iterable")

                new_loop_var = Iterable(loop_var.get_name(), Variable.FOR_LIST, iterable_var.get())

                self.symbolTable.change_value(loop_var.get_name(), new_loop_var)

                self.index += 1

            elif task.get_type() == AExpression.ENDFOR:
                if DEBUG:
                    print("DEBUG: ENDING FOR LOOP OR JUMP")
                #deal with scopes
                index, loop_var_name = task.get_content()
                loop_var = self.symbolTable.get(loop_var_name)
                if loop_var.next() != Iterable.EOL:
                    #On n'a pas encore parcouru toute la liste donc on retourne au début de la boucle
                    if DEBUG:
                        print("DEBUG: JUMP")
                    loop_var.increment()
                    self.index = index
                else:
                    #on regarde les instructions suivantes (et on réinitialise l'index de la variable de la boucle for)
                    if DEBUG:
                        print("DEBUG: ENDING FOR LOOP")
                    loop_var.index = 0
                    self.index += 1

            elif task.get_type() == AExpression.IF:
                if DEBUG:
                    print("DEBUG: IF")

                comparison = task.get_content()
                if comparison.get() == False:
                    self.index += 1
                    while self.stack[self.index].get_type() != AExpression.ENDIF:
                        self.index += 1

                self.index += 1

            elif task.get_type() == AExpression.ENDIF:
                self.index += 1

        print()
        return self._output_buffer


class AExpression:
    PRINT = "PRINT"
    VAR = "VAR"
    FOR = "FOR"
    ENDFOR = "ENDFOR"
    JUMP = "JUMP"
    IF = "IF"
    ENDIF = "ENDIF"

    def __init__(self, type, content):
        self._type = type
        self.content = content

    def get_content(self):
        return self.content

    def get_type(self):
        return self._type

    def __repr__(self):
        return f"{self._type}: {repr(self.content)}"

class Printing(AExpression):
    def __init__(self, content):
        super(Printing, self).__init__(AExpression.PRINT, content) #on stocke une variable

class VariableAssignment(AExpression):
    def __init__(self, content):
        super(VariableAssignment, self).__init__(AExpression.VAR, content) #on stocke une variable

class ForLoop(AExpression):
    def __init__(self, content):
        super(ForLoop, self).__init__(AExpression.FOR, content) #on stocke une variable et un itérable (tuple)

    def __repr__(self):
        return f"{self._type}: LOOP VARIABLE = {self.content[0].get_name()}"

class EndFor(AExpression):
    def __init__(self, content):
        super(EndFor, self).__init__(AExpression.ENDFOR, content) #index et le nom d'une variable (tuple)

    def __repr__(self):
        return f"{self._type}: JUMP TO INSTRUCTION {self.content[0]}, INCREMENT {self.content[1]}"

class Jump(AExpression):
    def __init__(self, content):
        super(Jump, self).__init__(AExpression.JUMP, content) #index

class If(AExpression):
    def __init__(self, content):
        super(If, self).__init__(AExpression.IF, content) #variable bool

class EndIf(AExpression):
    def __init__(self, content = None):
        super(EndIf, self).__init__(AExpression.ENDIF, None)

    def __repr__(self):
        return f"{self._type}"

# Création d'un transformateur, ébauche du projet
class DumboBlocTransformer(Transformer):
    def __init__(self, globalSymbolTable, DEBUG = False, *args, **kwargs):
        super(DumboBlocTransformer, self).__init__(*args, **kwargs)
        self._output_buffer = ""
        self.symbolTable = globalSymbolTable
        self.current_scope = self.symbolTable
        self.inter = IntermediateCodeHandler()

        self.DEBUG = DEBUG
        self.counter = 0

    def expression_list(self, items):
        return items

    def expression(self, items):
        return items

    def arithmetic_expression(self, items):
        if self.DEBUG:
            print("arithmetic_expression", self.counter)
            self.counter+=1

        if items[0] == "(":
            return items[1]

        result = items[0]
        if len(items) == 1:
            return result

        elif (items[1] == "-"):
            result -= items[2]
        elif (items[1] == "+"):
            result += items[2]
        elif items[1] == "*":
            return items[0] * items[2]
        else:
            return items[0] / items[2]

        return result

    def string_list_interior(self,items):
        if self.DEBUG:
            print("string_list_interior", self.counter)
            self.counter+=1

        result = [items[0]]
        if len(items) > 1:
            result += items[1]
        return result

    def string_list(self, items):
        if self.DEBUG:
            print("string_list", self.counter)
            self.counter+=1

        var = Variable("__ANON__", Variable.LIST, items[0])
        return var

    def string(self, items):
        if self.DEBUG:
            print("string", self.counter)
            self.counter+=1

        result = items[0].replace("'","")
        var = Variable("__ANON__", Variable.STRING, result)
        return var

    def dumbo_bloc(self, items):
        if self.DEBUG:
            print("dumbo_bloc", self.counter)
            self.counter+=1

        #create new scope
        return items

    def print_expression(self, items):
        if self.DEBUG:
            print("print_expression", self.counter)
            self.counter+=1

        #self._output_buffer += str(items[0].get()) + "\n"
        var = items[0]
        if items[0].get_name() != "__ANON__":
            var = Variable("__ANON__", Variable.REF, var.get_name())
        self.inter.add_instr(Printing(var))
        return None

    def for_loop_expression(self, items):
        if self.DEBUG:
            print("for_loop_expression", self.counter)
            self.counter+=1

        index_and_var_name, expression_list = items
        index, loop_var = index_and_var_name

        self.inter.add_instr(EndFor((index, loop_var.get_name())))

        return None #pas besoin de renvoyer quoi que ce soit, l'expression est terminée

    def loop_variable_assignment(self, items):
        if self.DEBUG:
            print("loop_variable_assignment", self.counter)
            self.counter+=1

        loop_var, iterable = items

        #initialisation de la variable de la boucle
        loop_var = Iterable(loop_var.get_name(), Variable.FOR_LIST, [Variable(None,None,None)])

        #check si la variable existe déjà dans la table des symboles
        #sinon, l'y ajouter
        if not loop_var.get_name() in self.current_scope:
            self.current_scope.add_content(loop_var)

        index = self.inter.add_instr(ForLoop((loop_var, iterable)))

        return (index, loop_var)

    def string_expression(self, items):
        if self.DEBUG:
            print("string_expression", self.counter)
            self.counter+=1

        for item in items:
            item_type = item.get_type()
            if item_type == None:
                raise NameError(f"name '{item.get_name()}' is not defined")

        if len(items) > 1:
            new_items = []
            for item in items:
                if item.get_name() != "__ANON__":
                    new_items.append(Variable("__ANON__", Variable.REF, item.get_name()))
                else:
                    new_items.append(item)
            return Variable("__ANON__", Variable.STRING_CONCAT, new_items)

        return items[0]

    def variable(self, items):
        if self.DEBUG:
            print("variable", items[0], self.counter)
            self.counter+=1

        if items[0] in self.current_scope:
            return self.current_scope.get(items[0])
        return Variable(items[0], None, None)

    def assignment_expression(self, items):
        if self.DEBUG:
            print("assignment_expression", self.counter)
            self.counter+=1

        var = items[2]

        if not var.get_type():
            raise NameError(f"name '{item.get_name()}' is not defined")

        if var.get_name() != "__ANON__":
            #var est un nom de variable qui est déjà référencé dans la table de symbole => référence
            new_var = Variable(items[0].get_name(), Variable.REF, var.get_name())
        else:
            #var est une variable anonyme donc on fait une assignation et pas une référence
            if var.get_type() == Variable.FOR_LIST:
                new_var = Iterable(items[0].get_name(), None, None)
            else:
                new_var = Variable(items[0].get_name(), None, None)
            new_var._type = var.get_type()
            new_var._value = var.get()

        #ajout de var dans le scope actuel si elle n'est pas encore dans la table des symboles
        if not new_var.get_name() in self.current_scope:
            self.current_scope.add_content(new_var)

        self.inter.add_instr(VariableAssignment(new_var))

        return None #pas besoin de retourner quoi que ce soit, l'expression est finie

    def signed_decimal_integer(self, items):
        if self.DEBUG:
            print("signed_decimal_integer", self.counter)
            self.counter+=1

        if (items[0] == "-"):
            items[1]._value = -items[1].get()
            return items[1]

        return items[1]

    def decimal_integer(self, items):
        if self.DEBUG:
            print("decimal_integer", self.counter)
            self.counter+=1

        if len(items) == 0:
            return Variable("__ANON__", Variable.INT, 0)
        return Variable("__ANON__", Variable.INT, int("".join(items)))

    def non_zero_digit(self, items):
        if self.DEBUG:
            print("non_zero_digit", self.counter)
            self.counter+=1

        return items[0].value

    def digit(self, items):
        if self.DEBUG:
            print("digit", self.counter)
            self.counter+=1

        if len(items) == 0:
            return "0"
        return items[0]

    def if_then_expression(self, items):
        if self.DEBUG:
            print("if_then_expression", self.counter)
            self.counter += 1

        comparison, expression_list = items

        #Add end if expression
        self.inter.add_instr(EndIf())

        return None

    def if_verification(self, items):
        if self.DEBUG:
            print("if_verification", self.counter)
            self.counter += 1

        print("comparison:", items)
        self.inter.add_instr(If(items[0]))

        return None

    def boolean_expression(self, items):
        if self.DEBUG:
            print("boolean_expression", self.counter)
            self.counter += 1

        print("items:", items)

        if len(items) > 1:
            if items[0] == "(":
                return items[1]

            b1, boolean_operator, b2 = items

            if boolean_operator == "or":
                print(b1.get() or b2.get())
                return Variable("__ANON__", Variable.BOOL, b1.get() or b2.get())
            else:
                print(b1.get() and b2.get())
                return Variable("__ANON__", Variable.BOOL, b1.get() and b2.get())

        if items[0] == "true":
            print("True", True)
            return Variable("__ANON__", Variable.BOOL, True)
        elif items[0] == "false":
            print("False", False)
            return Variable("__ANON__", Variable.BOOL, False)

        return items[0]

    def comparison_expression(self, items):
        if self.DEBUG:
            print("comparison_expression", self.counter)
            self.counter += 1

        decimal1, comparison_operator, decimal2 = items

        if comparison_operator == "<":
            return Variable("__ANON__", Variable.BOOL, decimal1.get() < decimal2.get())
        elif comparison_operator == ">":
            return Variable("__ANON__", Variable.BOOL, decimal1.get() > decimal2.get())
        elif comparison_operator == "=":
            return Variable("__ANON__", Variable.BOOL, decimal1.get() == decimal2.get())
        elif comparison_operator == "<=":
            return Variable("__ANON__", Variable.BOOL, decimal1.get() <= decimal2.get())
        elif comparison_operator == ">=":
            return Variable("__ANON__", Variable.BOOL, decimal1.get() >= decimal2.get())
        else:
            #comparison_operator == "!="
            return Variable("__ANON__", Variable.BOOL, decimal1.get() != decimal2.get())

    def get(self):
        return self.inter.execute(self.symbolTable, DEBUG = self.DEBUG)

#ouverture du fichier contenant la grammaire et création du parser à partir de cette grammaire
arithmetic_parser = Lark.open("../dumbo/dumbo.lark", parser='lalr', rel_to=__file__)

#ligne à tester avec la grammaire
input_to_parse = """
    {{
        if (true and false) and (true or false) do
            print 'ok';
        endif;

    }}
"""
"""{{
    a := 'test';
    i := ('a', 'b', 'c', 'd');
    i := ('t', 'e', 's', 't');
    print 'test ' . i ;
    a := ('0', '1', '2', '3');
    b := i;
    for i in b do
        print i;
    endfor;
    }}"""
"""
{{
    a := 'test';
    print a;
}}
"""

#parsing de la ligne de test et affichage du résultat
parsing = arithmetic_parser.parse(input_to_parse)
#print(parsing.pretty()) #affiche l'arbre du programme donné dans "input_to_parse"
globalSymbolTable = SymbolTable()
parsed = DumboBlocTransformer(globalSymbolTable, DEBUG = True) #ArithmeticTransformer(SymbolTable(), DEBUG = True)
parsed.transform(parsing)

print("\n######## parsed ########\n")

print("\n######## OUTPUT ########\n")

print(parsed.get())
#print("parsed", parsed.get()) #affiche l'output du parsing